(ns hirameki-patents.checks
  "The corpus's two checks, as functions that RETURN problems.

  `verify.clj` and `query-check.clj` were top-level scripts with side effects,
  which meant the only way to run them was to be a shell. The murakumo fleet
  runs `:jvm-test` gates (deps.edn `:test` alias, cognitect test-runner), so the
  checks had to become callable to be runnable by anything other than the
  machine that wrote the corpus.

  That is the point of putting them on the fleet at all: **right now the writer
  is also the only verifier.** A corpus corrupted on this machine is checked by
  this machine. Moving the check to a node that only has the git tree makes the
  two roles different.

  Both functions return a vector of problem strings — empty means clean. No
  printing, no exit codes; the CLI wrappers and the test namespace each decide
  what to do with them."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [datascript.core :as d]
            [multiformats.core :as mf]))

(def single-block-limit (* 256 1024))

(defn- read-manifest [dir]
  (edn/read-string (slurp (io/file dir "publish-manifest.edn"))))

(defn verify-artifacts
  "Re-derive every shard's CIDv1/raw/sha2-256 from the bytes on disk and compare
  to the manifest. Also checks the block limit and that the item counts add up —
  a CID proves a shard is intact, never that the SET of shards is complete."
  [dir]
  (let [manifest (read-manifest dir)
        problems (atom [])
        add! #(swap! problems conj %)]
    (doseq [[kind {:keys [parts rows bytes shards]}] (:artifacts manifest)]
      (when-not (= shards (count parts))
        (add! (str (name kind) ": manifest says " shards " shards but lists " (count parts))))
      (let [declared (reduce + 0 (map :bytes parts))]
        (when-not (= bytes declared)
          (add! (str (name kind) ": declared total " bytes " ≠ sum of parts " declared))))
      (doseq [{:keys [file cid] declared-bytes :bytes} parts]
        (let [f (io/file dir file)]
          (if-not (.exists f)
            (add! (str file ": missing"))
            (let [raw (.getBytes (slurp f) "UTF-8")
                  actual-bytes (alength raw)
                  actual-cid (mf/cidv1-raw raw)]
              (cond
                (not= declared-bytes actual-bytes)
                (add! (str file ": byte count " declared-bytes " ≠ actual " actual-bytes))
                (>= actual-bytes single-block-limit)
                (add! (str file ": " actual-bytes " bytes exceeds the raw-block limit"))
                (not= cid actual-cid)
                (add! (str file ": CID mismatch " cid " vs " actual-cid)))))))
      (let [read-back (reduce + 0 (map #(count (edn/read-string (slurp (io/file dir (:file %))))) parts))]
        (when-not (= rows read-back)
          (add! (str (name kind) ": manifest claims " rows " items but the shards hold " read-back)))))
    @problems))

(defn- datoms-db
  "Every datoms/ shard transacted into DataScript."
  [dir]
  (let [shards (->> (.listFiles (io/file dir "datoms"))
                    (filter #(str/ends-with? (.getName %) ".kotoba.edn"))
                    (sort-by #(.getName %)))
        raw (vec (mapcat #(edn/read-string (slurp %)) shards))
        by-entity (reduce (fn [acc [op e a v]]
                            (if (= ":db/add" op)
                              (update acc e (fnil conj []) [(keyword (subs a 1)) v])
                              acc))
                          {} raw)
        conn (d/create-conn {:hirameki/entity-id {:db/unique :db.unique/identity}})]
    (d/transact! conn (vec (for [[e attrs] by-entity] (into {:hirameki/entity-id e} attrs))))
    {:db @conn :raw raw}))

(defn query-corpus
  "Assert the published corpus ANSWERS QUESTIONS, not merely that it hashes.

  A set of shards can hash perfectly and still transact into a shape where the
  attribute you wanted to join on is not there. And G1/G2/G6 are checked on the
  PUBLISHED ARTIFACT rather than only in the code that wrote it."
  [dir]
  (let [{:keys [db raw]} (datoms-db dir)
        problems (atom [])
        add! #(swap! problems conj %)
        titled (d/q '[:find (count ?e) . :where [?e :hirameki.patent/title _]] db)
        assignees (d/q '[:find ?a (count ?e) :where [?e :hirameki.patent/assignee ?a]] db)
        jurisdictions (d/q '[:find ?j (count ?e) :where [?e :hirameki.patent/jurisdiction ?j]] db)
        expired (d/q '[:find ?e ?y :where [?e :hirameki.obs/years-to-expiry ?y] [(< ?y 0)]] db)
        attrs (into #{} (map #(nth % 2)) raw)]
    (when-not (and titled (pos? titled)) (add! "no patent carries a title"))
    (when-not (> (count assignees) 50)
      (add! (str "assignee is not a usable join key: " (count assignees) " distinct")))
    (when-not (> (count jurisdictions) 5)
      (add! (str "jurisdiction does not roll up: " (count jurisdictions) " distinct")))
    (when-not (pos? (count expired))
      (add! "the release clock is not numerically comparable"))
    (when (some #(re-find #"infringement|fto|equity-signal" (str %)) attrs)
      (add! "a verdict attribute is published (G1/G3)"))
    (when (some #(re-find #"imposes" (str %)) attrs)
      (add! "a patent imposes on something (G2)"))
    (when (some #(re-find #"inventor|person" (str %)) attrs)
      (add! "a person-level attribute is published (G6)"))
    {:problems @problems
     :stats {:patents titled :assignees (count assignees)
             :jurisdictions (count jurisdictions) :past-term (count expired)
             :attributes (count attrs) :datoms (count raw)}}))
