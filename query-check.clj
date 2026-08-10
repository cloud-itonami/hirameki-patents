;; query-check.clj — prove the published corpus is QUERYABLE, not just intact.
;;
;;   clojure -M:query query-check.clj
;;
;; A thin wrapper over `src/hirameki_patents/checks.clj` (see verify.clj).
;;
;; verify.clj proves the bytes are what the manifest says. That is a different
;; claim from "you can ask this corpus a question": a set of shards can hash
;; perfectly and still transact into a shape where the attribute you wanted to
;; join on is not there. This transacts every datoms/ shard into DataScript and
;; runs the queries the corpus is supposed to answer, and asserts G1/G2/G6 hold
;; in the PUBLISHED ARTIFACT rather than only in the code that wrote it.
(require '[hirameki-patents.checks :as checks])

(let [{:keys [problems stats]} (checks/query-corpus ".")]
  (println (format "query-check — %d datoms, %d patents, %d assignees, %d jurisdictions, %d past term"
                   (:datoms stats) (:patents stats) (:assignees stats)
                   (:jurisdictions stats) (:past-term stats)))
  (if (seq problems)
    (do (println "FAILED:")
        (doseq [p problems] (println "  ✗" p))
        (System/exit 1))
    (println "the published corpus answers every query it claims to")))
