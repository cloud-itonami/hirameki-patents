;; verify.clj — trustless verification of the published corpus.
;;
;;   clojure -M:query verify.clj
;;
;; A thin wrapper. The checks live in `src/hirameki_patents/checks.clj` so that
;; the murakumo fleet can run them as a `:jvm-test` gate — a node with the git
;; tree and nothing else becomes the verifier, instead of the machine that wrote
;; the corpus checking its own work.
;;
;; Re-derives every shard's CIDv1/raw/sha2-256 from the bytes on disk and
;; compares to publish-manifest.edn. No IPFS daemon, no network, no trust in
;; whoever served you the file. Also checks the item counts add up — a CID
;; proves a shard is intact, never that the SET of shards is complete.
(require '[hirameki-patents.checks :as checks]
         '[clojure.string :as str])

(let [problems (checks/verify-artifacts ".")]
  (if (seq problems)
    (do (println "FAILED:")
        (doseq [p problems] (println "  ✗" p))
        (System/exit 1))
    (println "all shards verified — bytes, CIDs and item counts agree with the manifest")))
