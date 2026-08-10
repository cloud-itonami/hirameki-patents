;; query-check.clj — prove the published corpus is actually QUERYABLE.
;;
;;   clojure -M:query query-check.clj
;;
;; `verify.clj` proves the bytes are what the manifest says. That is a different
;; claim from "you can ask this corpus a question": a set of shards can hash
;; perfectly and still be un-transactable, or transact into a shape where the
;; attribute you want to join on does not exist.
;;
;; So this loads every `datoms/*.kotoba.edn` shard into DataScript and runs real
;; queries. It is a GATE, not a demo: it exits 1 when a query that should return
;; rows returns none.
;;
;; ## Why the attributes are strings here
;;
;; The published datoms are `[":db/add" e a v]` with STRING attribute names, and
;; that is deliberate (the workspace convention, CLAUDE.md docs-edn-only): the
;; datascript.js reader used by `manifest/edn-query.cljs` takes bare strings. The
;; same artifact transacts into Datomic by reading those strings as keywords —
;; the shape is one substitution away in either direction, and neither reader
;; needs the other's.
(require '[clojure.edn :as edn]
         '[clojure.java.io :as io]
         '[clojure.string :as str]
         '[datascript.core :as d])

(def problems (atom []))
(defn- check! [label ok? detail]
  (if ok?
    (println (format "  ok    %-42s %s" label detail))
    (do (println (format "  FAIL  %-42s %s" label detail))
        (swap! problems conj label))))

(def shards
  (->> (.listFiles (io/file "datoms"))
       (filter #(str/ends-with? (.getName %) ".kotoba.edn"))
       (sort-by #(.getName %))))

(def raw (vec (mapcat #(edn/read-string (slurp %)) shards)))

(println (format "query-check — %d shard(s), %d datoms" (count shards) (count raw)))

;; ":db/add" e a v  →  {:db/id <tempid for e> <attr-kw> v}
;; Entities are string ids (`hirameki-patent:US8697359B1`), so they need mapping
;; to DataScript's numeric ids; the string id is kept as :hirameki/entity-id so
;; a caller can still get back to the source record.
(def by-entity
  (reduce (fn [acc [op e a v]]
            (if (= ":db/add" op)
              (update acc e (fnil conj []) [(keyword (subs a 1)) v])
              acc))
          {} raw))

(def schema
  {:hirameki.patent/assignee {:db/cardinality :db.cardinality/one}
   :hirameki/entity-id {:db/unique :db.unique/identity}})

(def conn (d/create-conn schema))

(d/transact! conn
             (vec (for [[e attrs] by-entity]
                    (into {:hirameki/entity-id e} attrs))))

(def db @conn)

;; ── the queries ─────────────────────────────────────────────────────────────

(let [n (d/q '[:find (count ?e) . :where [?e :hirameki.patent/title _]] db)]
  (check! "patents are transactable" (and n (pos? n)) (str n " with a title")))

(let [rows (d/q '[:find ?a (count ?e)
                  :where [?e :hirameki.patent/assignee ?a]]
                db)]
  (check! "assignee is a joinable attribute" (> (count rows) 50)
          (str (count rows) " distinct assignees")))

(let [rows (d/q '[:find ?j (count ?e)
                  :where [?e :hirameki.patent/jurisdiction ?j]]
                db)]
  (check! "jurisdiction rolls up" (> (count rows) 5)
          (str (count rows) " jurisdictions")))

(let [rows (d/q '[:find ?title ?s
                  :in $ ?assignee
                  :where
                  [?e :hirameki.patent/assignee ?assignee]
                  [?e :hirameki.patent/title ?title]
                  [?e :hirameki.obs/release-status ?s]]
                db ":kansai-paint")]
  (check! "join by holder returns its patents" (pos? (count rows))
          (str (count rows) " for :kansai-paint")))

(let [rows (d/q '[:find ?e ?y
                  :where
                  [?e :hirameki.obs/years-to-expiry ?y]
                  [(< ?y 0)]]
                db)]
  (check! "the release clock is numeric and comparable" (pos? (count rows))
          (str (count rows) " already past their term")))

;; G1/G2/G6 hold in the PUBLISHED artifact, not only in the code that wrote it.
(let [attrs (into #{} (map #(nth % 2)) raw)]
  (check! "no verdict attribute is published"
          (not-any? #(re-find #"infringement|fto|equity-signal" (str %)) attrs)
          (str (count attrs) " distinct attributes"))
  (check! "no patent imposes on anything (G2)"
          (not-any? #(re-find #"imposes" (str %)) attrs) "")
  (check! "no person-level inventor attribute (G6)"
          (not-any? #(re-find #"inventor|person" (str %)) attrs) ""))

(if (seq @problems)
  (do (println (str "\nFAILED: " (str/join ", " @problems)))
      (System/exit 1))
  (println "\nthe published corpus answers every query it claims to"))
