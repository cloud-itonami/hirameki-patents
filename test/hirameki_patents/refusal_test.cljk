(ns hirameki-patents.refusal-test
  "The two corpus checks, made to REFUSE.

  `corpus-test` asserts the published corpus is clean, which is worth having but
  is positive-only: it can report that today's bytes hash to what the manifest
  says, and nothing else. **Neither check had ever been observed to reject
  anything.** Measured 2026-09-10 against the tree at 60a6cc5: disabling the CID
  comparison, the raw-block limit, and all three of the G1/G2/G6 governance
  guards — five refusals, disabled at once — left the suite reporting
  `0 failures, 0 errors`.

  That is the sixth question of ADR-2608136000: *has this check ever refused for
  the reason it names?* A check run only against clean input returns the same
  verdict whether it is working or absent, so its green says nothing.

  Each test below builds a small corpus on disk that is wrong in exactly one
  way, and asserts both that the check refuses AND that it refuses **for the
  named reason**. The reason literal is pinned deliberately: a guard that starts
  refusing for some other cause has stopped doing the job it is named for, and
  should not be able to keep a test green by failing coincidentally.

  Why fixtures rather than the real corpus: these are refusals about bytes that
  do not match their manifest, and shards over the block limit. The published
  corpus cannot hold either without the repo being broken, so the only way to
  watch the refusal fire is to hand it something wrong on purpose."
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.edn :as edn]
            [clojure.java.io :as io]
            [datascript.core]
            [kotoba.lang.text]
            [multiformats.core :as mf]
            [hirameki-patents.checks :as checks])
  (:import (java.nio.file Files)
           (java.nio.file.attribute FileAttribute)))

;; ---------------------------------------------------------------- fixtures

(defn- tmpdir []
  (.toFile (Files/createTempDirectory "hirameki-refusal" (into-array FileAttribute []))))

(defn- delete-tree! [f]
  (when (.isDirectory f) (run! delete-tree! (.listFiles f)))
  (.delete f))

(defn- names-reason?
  "Does exactly one problem name `substr`? Substring, not regex — the point is to
  pin the literal the check prints, so a rename of the reason is a failure."
  [problems substr]
  (= 1 (count (filter #(.contains ^String % ^String substr) problems))))

(defn- write-shard!
  "Write `text` under `dir` and return the manifest part that describes it
  CORRECTLY. Every perturbation below is applied to this, so exactly one field
  is ever wrong."
  [dir rel text]
  (let [f (io/file dir rel)
        raw (.getBytes ^String text "UTF-8")]
    (io/make-parents f)
    (spit f text)
    {:file rel :bytes (alength raw) :cid (mf/cidv1-raw raw)}))

(defn- corpus-fixture!
  "A directory holding one correctly-described shard whose EDN is `text`."
  [text n-items]
  (let [dir (tmpdir)
        part (write-shard! dir "corpus/000.kotoba.edn" text)]
    {:dir dir
     :artifacts {:corpus {:parts [part] :rows n-items :bytes (:bytes part) :shards 1}}}))

(defn- clean-corpus! []
  (corpus-fixture! (pr-str [{:id "P-1"} {:id "P-2"}]) 2))

(defn- edn-of-exactly
  "EDN text of exactly `n` bytes holding one item. `[{:pad \"` + `\"}]` is 11
  ASCII bytes, so the padding carries the rest."
  [n]
  (str "[{:pad \"" (apply str (repeat (- n 11) \x)) "\"}]"))

(defn- verify-problems
  "Write the manifest, run verify-artifacts, clean up."
  [{:keys [dir artifacts]}]
  (try
    (spit (io/file dir "publish-manifest.edn") (pr-str {:artifacts artifacts}))
    (checks/verify-artifacts dir)
    (finally (delete-tree! dir))))

;; ------------------------------------------------- verify-artifacts refusals

(deftest a-correctly-described-corpus-is-accepted
  (testing "the control. Without it, every refusal below could be the fixture
            being malformed rather than the perturbation being caught"
    (is (empty? (verify-problems (clean-corpus!))))))

(deftest refuses-a-cid-that-does-not-match-the-bytes
  (testing "a shard whose declared CID belongs to different bytes — the one
            thing the manifest exists to make checkable"
    (let [wrong (mf/cidv1-raw (.getBytes "not this shard" "UTF-8"))
          problems (verify-problems
                    (assoc-in (clean-corpus!) [:artifacts :corpus :parts 0 :cid] wrong))]
      (is (seq problems))
      (is (names-reason? problems "CID mismatch")))))

(deftest refuses-a-byte-count-that-does-not-match-the-file
  (let [problems (verify-problems
                  (update-in (clean-corpus!) [:artifacts :corpus :parts 0 :bytes] inc))]
    (is (names-reason? problems "byte count"))))

(deftest refuses-a-shard-the-manifest-names-but-does-not-exist
  (testing "a shard that never got uploaded — and the check RETURNS that, rather
            than throwing on the way to reporting it. Written 2026-09-10, this
            test failed with a FileNotFoundException: the missing shard was
            detected, then the row-count readback slurped every part
            unconditionally and died before the report came back. A crash is not
            a refusal — from the caller's side it is indistinguishable from the
            checker being broken"
    (let [problems (verify-problems
                    (assoc-in (clean-corpus!) [:artifacts :corpus :parts 0 :file]
                              "corpus/nonexistent.kotoba.edn"))]
      (is (names-reason? problems "missing"))
      (testing "and the shortfall is still counted, not swallowed with the file"
        (is (names-reason? problems "items but the shards hold"))))))

(deftest refuses-a-shard-count-that-disagrees-with-the-parts-listed
  (testing "a CID proves a shard is intact, never that the SET of shards is
            complete — this is the check that covers the difference"
    (let [problems (verify-problems
                    (assoc-in (clean-corpus!) [:artifacts :corpus :shards] 2))]
      (is (names-reason? problems "shards but lists")))))

(deftest refuses-a-declared-total-that-is-not-the-sum-of-its-parts
  (let [problems (verify-problems
                  (update-in (clean-corpus!) [:artifacts :corpus :bytes] + 100))]
    (is (names-reason? problems "sum of parts"))))

(deftest refuses-a-row-count-the-shards-do-not-hold
  (testing "the manifest claiming more items than the shards actually contain —
            silent truncation, which hashes perfectly shard by shard"
    (let [problems (verify-problems
                    (assoc-in (clean-corpus!) [:artifacts :corpus :rows] 99))]
      (is (names-reason? problems "items but the shards hold")))))

(deftest refuses-a-shard-at-exactly-the-block-limit
  (testing "the boundary. `>=` and `>` differ only on the line itself, so a
            comparison with no input ON the line is an untested comparison
            (ADR-2608136000, question 5)"
    (let [problems (verify-problems (corpus-fixture! (edn-of-exactly checks/single-block-limit) 1))]
      (is (names-reason? problems "exceeds the raw-block limit")))))

(deftest accepts-a-shard-one-byte-under-the-block-limit
  (testing "the other side of that same line — without this, moving the limit
            up would go unnoticed"
    (is (empty? (verify-problems
                 (corpus-fixture! (edn-of-exactly (dec checks/single-block-limit)) 1))))))

;; ---------------------------------------------------- query-corpus refusals

(defn- base-tuples
  "Datoms that answer every question `query-corpus` asks."
  [{:keys [n titles? jurisdictions expiries?]
    :or {n 60 titles? true jurisdictions 8 expiries? true}}]
  (vec (for [i (range n)
             [a v] (cond-> [[":hirameki.patent/assignee" (str ":assignee-" i)]
                            [":hirameki.patent/jurisdiction" (str ":j" (mod i jurisdictions))]
                            [":hirameki.obs/years-to-expiry" (if expiries? (- i 30) (+ i 30))]]
                     titles? (conj [":hirameki.patent/title" (str "Patent " i)]))]
         [":db/add" (str "hirameki-patent:P-" i) a v])))

(defn- query-problems
  "Transact `tuples` as the whole datoms/ plane, run query-corpus, clean up."
  [tuples]
  (let [dir (tmpdir)]
    (try
      (let [f (io/file dir "datoms/000.kotoba.edn")]
        (io/make-parents f)
        (spit f (pr-str tuples)))
      (:problems (checks/query-corpus dir))
      (finally (delete-tree! dir)))))

(deftest a-corpus-that-answers-every-question-is-accepted
  (testing "the control for the query side"
    (is (empty? (query-problems (base-tuples {}))))))

(deftest refuses-a-published-verdict-attribute
  (testing "G1/G3 — the corpus publishes bibliographic fact, never a judgement
            about whether someone infringes. This is a governance boundary, so
            it has to be shown refusing, not assumed"
    (doseq [attr [":hirameki.patent/infringement-risk"
                  ":hirameki.obs/fto-status"
                  ":hirameki.obs/equity-signal"]]
      (let [problems (query-problems
                      (conj (base-tuples {}) [":db/add" "hirameki-patent:P-0" attr ":high"]))]
        (is (names-reason? problems "a verdict attribute is published (G1/G3)")
            (str "not refused for: " attr))))))

(deftest refuses-a-patent-that-imposes-on-something
  (testing "G2"
    (let [problems (query-problems
                    (conj (base-tuples {})
                          [":db/add" "hirameki-patent:P-0" ":hirameki.patent/imposes-on" "X"]))]
      (is (names-reason? problems "a patent imposes on something (G2)")))))

(deftest refuses-a-person-level-attribute
  (testing "G6 — inventors are people, and this corpus is public"
    (doseq [attr [":hirameki.patent/inventor" ":hirameki.patent/person-name"]]
      (let [problems (query-problems
                      (conj (base-tuples {}) [":db/add" "hirameki-patent:P-0" attr "A Name"]))]
        (is (names-reason? problems "a person-level attribute is published (G6)")
            (str "not refused for: " attr))))))

(deftest refuses-a-corpus-where-nothing-carries-a-title
  (let [problems (query-problems (base-tuples {:titles? false}))]
    (is (names-reason? problems "no patent carries a title"))))

(deftest refuses-an-assignee-that-is-not-a-usable-join-key
  (testing "shards can hash perfectly and still transact into a shape with too
            few distinct assignees to join on"
    (let [problems (query-problems (base-tuples {:n 10}))]
      (is (names-reason? problems "assignee is not a usable join key")))))

(deftest refuses-a-jurisdiction-that-does-not-roll-up
  (let [problems (query-problems (base-tuples {:jurisdictions 1}))]
    (is (names-reason? problems "jurisdiction does not roll up"))))

(deftest refuses-a-release-clock-that-is-not-numerically-comparable
  (testing "years-to-expiry present but never negative — the clock reads as a
            label rather than a number you can order"
    (let [problems (query-problems (base-tuples {:expiries? false}))]
      (is (names-reason? problems "the release clock is not numerically comparable")))))
