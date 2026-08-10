;; verify.clj — trustless verification of the published corpus.
;;
;;   clojure -M verify.clj
;;
;; Re-derives every shard's CIDv1/raw/sha2-256 from the bytes on disk and
;; compares it to `publish-manifest.edn`. No IPFS daemon, no network, no trust
;; in whoever served you the file.
;;
;; Each shard is deliberately kept under the 256 KiB chunker limit so that a raw
;; single-block CID is exactly what `ipfs add --cid-version=1 --raw-leaves`
;; produces. Past that limit IPFS builds a UnixFS DAG whose root is a `bafybei…`
;; dag-pb CID — a different value entirely, and one this file could not check.
(require '[clojure.edn :as edn]
         '[clojure.java.io :as io]
         '[multiformats.core :as mf])

(def single-block-limit (* 256 1024))

(let [manifest (edn/read-string (slurp "publish-manifest.edn"))
      problems (atom [])]
  (doseq [[kind {:keys [parts rows bytes shards]}] (:artifacts manifest)]
    (println (format "%s — %s items, %s bytes, %s shard(s)"
                     (name kind) rows bytes shards))
    (when-not (= shards (count parts))
      (swap! problems conj (str (name kind) ": manifest says " shards
                                " shards but lists " (count parts))))
    (let [declared (reduce + 0 (map :bytes parts))]
      (when-not (= bytes declared)
        (swap! problems conj (str (name kind) ": declared total " bytes
                                  " ≠ sum of parts " declared))))
    (doseq [{:keys [file cid] declared-bytes :bytes} parts]
      (let [f (io/file file)]
        (cond
          (not (.exists f))
          (swap! problems conj (str file ": missing"))

          :else
          (let [content (slurp f)
                raw (.getBytes content "UTF-8")
                actual-bytes (alength raw)
                actual-cid (mf/cidv1-raw raw)]
            (cond
              (not= declared-bytes actual-bytes)
              (swap! problems conj (str file ": byte count " declared-bytes
                                        " ≠ actual " actual-bytes))

              (>= actual-bytes single-block-limit)
              (swap! problems conj (str file ": " actual-bytes
                                        " bytes exceeds the raw-block limit — a raw CID"
                                        " is not what `ipfs add` would produce here"))

              (not= cid actual-cid)
              (swap! problems conj (str file ": CID mismatch\n    manifest " cid
                                        "\n    actual   " actual-cid))

              :else
              (println (format "  ok  %-28s %8d bytes  %s" file actual-bytes cid))))))))

  ;; The row counts are the part a CID cannot vouch for: every shard can be
  ;; internally perfect while the set of shards is missing one.
  (doseq [[kind {:keys [parts rows]}] (:artifacts manifest)]
    (let [read-back (reduce + 0 (map #(count (edn/read-string (slurp (:file %)))) parts))]
      (when-not (= rows read-back)
        (swap! problems conj (str (name kind) ": manifest claims " rows
                                  " items but the shards hold " read-back)))))

  (if (seq @problems)
    (do (println "\nFAILED:")
        (doseq [p @problems] (println "  ✗" p))
        (System/exit 1))
    (println "\nall shards verified — bytes, CIDs and item counts agree with the manifest")))
