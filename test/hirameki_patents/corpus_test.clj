(ns hirameki-patents.corpus-test
  "The corpus checks, as a test suite the murakumo fleet can run.

  These are the same two checks the CLI wrappers run. They exist as a `:test`
  alias so a fleet node — which has the git tree and nothing else — can be the
  verifier. Until now the machine that WROTE the corpus was also the only thing
  that ever checked it."
  (:require [clojure.test :refer [deftest is testing]]
            [hirameki-patents.checks :as checks]))

(def dir ".")

(deftest artifacts-match-the-manifest
  (testing "every shard's bytes and CIDv1 are what publish-manifest.edn names,
            no shard exceeds the raw-block limit, and the item counts add up"
    (let [problems (checks/verify-artifacts dir)]
      (is (empty? problems) (str "\n  " (clojure.string/join "\n  " problems))))))

(deftest corpus-answers-queries
  (let [{:keys [problems stats]} (checks/query-corpus dir)]
    (testing (str "the published datoms transact and answer: " (pr-str stats))
      (is (empty? problems) (str "\n  " (clojure.string/join "\n  " problems))))
    (testing "the corpus is not trivially small — a gate that passes on an empty
              corpus would pass on a deleted one"
      (is (> (:patents stats) 100))
      (is (> (:datoms stats) 1000)))))
