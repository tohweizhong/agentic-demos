# Repository Notes: agentic-demos

Decisions and open questions for the repository as a whole. Each demo folder may
hold its own `NOTES.md` for decisions that apply only to that demo.

`README.md` says what each folder holds. `AGENTS.md` says the rules. This file
says why the structure is the way it is.

Last updated: 21 Sep 2026 SGT.

---

## 1. The three codelabs

| Lab folder | Authoring source | Published state | Reference implementation |
|---|---|---|---|
| `organic-chem-agent` | `CODELAB.md` | Live | Same folder, `app/` |
| `agy-im8-agent` | `CODELAB.md` | Staged preview only | Same folder, `app/` |
| `nus-agy-workshop` | `index.lab.md` | Live | Separate folder, `nus-transit-hub/` |

Find them with `ls */CODELAB.md`. This command misses `nus-agy-workshop` today,
because that lab has no `CODELAB.md`. Section 5 holds the fix.

---

## 2. Three roles hide in each lab folder

People confuse the first two. The reference implementation is not authoring
source. It is the product of the lab text. If you cannot recreate `app/` by
following `CODELAB.md`, the lab is broken.

| Role | What it is | Who edits it | Tracked |
|---|---|---|---|
| Authoring source | The lab text, images, metadata, publish recipe | You, by hand | Yes |
| Reference implementation | The finished code the lab produces | Regenerated, then committed | Yes |
| Trial run | A throwaway copy built by following the prompts | Nobody. It is output. | No |

### The real fault line

Folder layout is the smaller problem. The distinction that matters is whether
the published file is generated or hand-written.

- `organic-chem-agent` and `agy-im8-agent` hand-write `CODELAB.md`. The
  published `index.lab.md` is generated and never committed. Source and output
  stay apart.
- `nus-agy-workshop` hand-writes `index.lab.md` itself. The source is the
  output. There is no separation.

### The evidence that the missing split hurts

`nus-agy-workshop` holds two image folders, `images/` and `img/`. They are
byte-identical. Each holds 23 files. The lab text points at `img/` 27 times and
at `images/` zero times. So 23 files are dead, and nothing can tell you which
folder is correct, because no build step ever chooses.

### The proposed rules

1. One source name everywhere: `CODELAB.md`.
2. Never commit `index.lab.md`. Generate it at publish time. Ignore it in git.
3. One image folder for each lab.
4. Keep the answer key in the lab folder. `nus-transit-hub` is the exception,
   because the lab tells the attendee to type `npx create-next-app
   nus-transit-hub`. The folder name is part of the lesson. Leave it, but link
   both ways. Today only the implementation links back to the lab.
5. Restore the start state with git, not with tags. `agy-im8-agent` already does
   this. `git checkout -- sample_target_repo` resets the defects.
6. Trial runs go in a `trials/` folder that git ignores.

### A marker for answer-key files

Put one line at the top of every file the lab tells the attendee to create:

```python
# Reference implementation. CODELAB.md step 6 produces this file.
# If you edit this by hand, update step 6.
```

Not applied yet. It is cheap and it needs no tooling.

---

## 3. Decided: no `codelab-` folder prefix

The prefix would group the labs in a directory listing. It costs more than it
pays.

- The attendee sees the folder name. The NUS lab tells the attendee to type
  `nus-transit-hub`. A prefix would be wrong where the name matters most.
- A prefix stores a role in a name, and names do not update themselves.
- It creates a second index that competes with `README.md`.

Use the presence of `CODELAB.md` instead. A lab cannot work without its guide,
so the marker cannot fall out of step. Add the word **Codelab** to the
`README.md` entry for each lab, so a reader knows before opening the folder.

Reconsider at roughly ten labs.

---

## 4. Open decision: a separate repository for the codelabs

Not decided. Nothing has been changed.

### What forced the question

`nus-agy-workshop/OWNERS` lists a co-author. Assume the co-author may need to
push changes to that lab.

### CODEOWNERS cannot solve this

GitHub enforces permissions at the repository level, never at the folder level.
A user with write access can push to any folder. CODEOWNERS only requests
reviews. It has no effect without branch protection and pull requests. This
repository commits straight to `main`, so CODEOWNERS would do nothing.

### The two options that work

| Option | Co-author needs write access | Migration cost | Review cost |
|---|---|---|---|
| A. Fork and pull request | No | None | One review for each change |
| B. Separate codelabs repository | Yes, to the labs only | Real | None |

Option A solves the stated problem. The co-author forks the repository, edits
the lab, and opens a pull request. He never needs push access, so the other
demo folders are never at risk.

### Option B has an unsolved problem

Where does `nus-transit-hub` go? It is the answer key for the NUS lab, and
`README.md` also lists it as a demo.

- Leave it behind, and the lab and its answer key sit in different
  repositories. That is the drift risk from section 2, made worse.
- Move it, and the codelabs repository holds a full Next.js application.

Answer this before starting a split. The other two labs move cleanly, because
each holds its own answer key.

### Other arguments against a split

- The answer key is often also a demo. `organic-chem-agent` serves both roles.
- A repository boundary is a stronger version of the split that already failed
  inside `nus-agy-workshop`.
- The published IM8 lab points at this repository in its feedback link. A move
  breaks it.
- Three labs and one maintainer. Two repositories mean two rules files, two
  ignore files, and two audit passes before each commit.

### Clone size, for the record

| Item | Size |
|---|---|
| Whole repository, without `.git` | 168 MB |
| `nus-agy-workshop` | 11 MB |
| `organic-chem-agent` | 3.4 MB |
| `agy-im8-agent` | 136 KB |

A learner downloads 168 MB to reach a 136 KB lab. Two things reduce the
concern. About 5 MB of `nus-agy-workshop` is the duplicate image folder.
More importantly, the labs are prompt-driven, so the attendee builds the code
in Antigravity and never clones.

### Recommendation on the table

Take option A now. Split when a second co-authored lab appears, or when the
review load becomes a real cost.

---

## 5. Pending clean-up work

None of this is done.

1. Remove the internal links from this public repository. Section 1 of
   `AGENTS.md` bars them. Three places hold them:
   - `nus-agy-workshop/OWNERS` holds a `go/` shortlink. A publishing tool wrote
     the file and will overwrite it, so removing the link is not durable. Decide
     whether to ignore the file instead.
   - `ge-prober/docs/streamassist_and_connectors_deep_dive.md` holds three `go/`
     links and three internal source paths.
   - `ae_ge_publish/ADK_with_Agent_Engine_Integration_with_AgentSpace.ipynb`
     holds an internal issue link, a `go/` link, and an internal console link.
2. Delete `nus-agy-workshop/images/`. Keep `img/`, because the published lab
   resolves that path.
3. Rename `nus-agy-workshop/index.lab.md` to `CODELAB.md`. Add `index.lab.md`
   to the ignore file.
4. Add the word **Codelab** to the `README.md` entry for each of the three labs.
5. Amend section 5 of `AGENTS.md`. It states "Solo repository. Commit directly
   to `main`. Do not open a pull request." The premise no longer holds. It
   should read: direct commits for the maintainer, pull requests for outside
   contributors.
