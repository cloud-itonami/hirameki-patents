(require '[clojure.edn :as edn]
         '[multiformats.core :as mf])
(import '[java.nio.file Files Paths])

(let [manifest (edn/read-string (slurp "publish-manifest.edn"))]
  (doseq [[artifact {:keys [file bytes cid]}] (:artifacts manifest)]
    (let [path (Paths/get file (make-array String 0))
          content (Files/readAllBytes path)
          actual-cid (mf/cidv1-raw content)]
      (assert (= bytes (alength content)) (str artifact " byte count mismatch"))
      (assert (= cid actual-cid) (str artifact " CID mismatch"))
      (println artifact bytes cid))))
