# fundação

The machine that makes a codebase build things properly without anyone having
to remember.

*[Português](README.md)*

[![testes](https://github.com/oliveirarenanfelipe/nao-depende-de-lembrar/actions/workflows/testes.yml/badge.svg)](https://github.com/oliveirarenanfelipe/nao-depende-de-lembrar/actions/workflows/testes.yml)
[![codeql](https://github.com/oliveirarenanfelipe/nao-depende-de-lembrar/actions/workflows/codeql.yml/badge.svg)](https://github.com/oliveirarenanfelipe/nao-depende-de-lembrar/actions/workflows/codeql.yml)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![licenca](https://img.shields.io/badge/licen%C3%A7a-MIT-green)
![dependencias](https://img.shields.io/badge/depend%C3%AAncias-nenhuma-lightgrey)

> Heads up: the code, the comments and the terminal output are in Portuguese.
> This page explains what each piece does, so you can decide whether it is
> worth your time before you open the source.

---

Everyone working with a coding agent ends up with the same pile of rules:
always write a test, never commit a secret, record the decision. They live in
a `CLAUDE.md`, an `AGENTS.md`, a `.cursorrules`. The agent reads them, agrees,
and forgets by the next session.

The diagnosis that started this repository was put like this:

> *"there's a lot we don't do. or we do it and I don't know about it, or we do
> it sometimes and forget other times, and it depends on me remembering to
> ask."*

A rule written in prose holds nothing. What holds is one piece that measures,
and another that refuses. That is what this is.

---

## The rule behind everything here

> A warning that never fails anything is decoration.

No piece here exists to suggest. Each one either returns a number you can
check, or refuses to write the file. And each one proves its own result before
it writes:

- `ligar_ci` runs the test command before writing the workflow. If the test
  fails, there is no CI. A CI running the wrong command goes green without
  testing anything, and a false green is worse than a red one, because nobody
  looks again;
- `destilar` measures its own output before publishing. If one line still
  carries private context, it writes nothing and shows you the line;
- `inventario` executes each piece's test. A piece that exists, has a caller
  and whose test fails is not live: it is broken, and the map says so.

---

## What is in here

### measurement: answer with a number, not an impression

| piece | the question it answers |
|---|---|
| `o_basico.py` | *does every project cover the basics?* Seven items per project: identity, is a git repo, `.gitignore`, has a test written, the CI actually runs the test, secret scanning, decisions recorded |
| `inventario.py` | *is the machine standing?* Per piece: does it exist on disk, does anything call it, does its test pass right now |

`o_basico` deliberately separates "has a test" from "the CI runs the test".
That is the pair almost every project lies to itself about.

### repair: write the fix, don't list it

| piece | what it does |
|---|---|
| `ligar_ci.py` | detects the test shape a project already has (`pytest`, `npm test`, `go test`, a house script), runs the command, and only then writes the workflow |
| `consertar.py` | writes what is missing into the working tree (identity, secret scanning, `.gitignore`) and shows you what it wrote. You are the one who commits |

### rulers: move a judgement call out of the eye and into arithmetic

| piece | what it decides |
|---|---|
| `regua_de_trava.py` | which publication lock a project requires, read from the project's own contract (`efeito_no_mundo`, `dado_de_cliente`, `lifecycle`). It returns three parts, and dropping any of them makes it useless: what is recommended, what it costs, and the way out that exists today |
| `regua_de_complexidade.py` | how much process rigour a task deserves. Five dimensions scored 1 to 5 decide `SIMPLE`, `STANDARD` or `COMPLEX` |

The lock ruler is derived rather than generic for one reason: "is this project
serious?" is a question each day answers differently, and advice that does not
change with the answer becomes noise people learn to skip.

### the gate: the half that refuses

| piece | what it blocks |
|---|---|
| `bash_na_porta.py` | a shell command that could destroy your work, **before it runs**. Four axes: destroying the agent's folder, deleting something owned by another project, writing into another project via Bash, and corrupting accented text in a heredoc or a search |
| `fronteira_lib.py` | blocks nothing by itself: it is the only thing that answers *which project does this path belong to?*, and the gates ask it |

This is the piece the rest of the repository describes and did not ship. The
others measure and repair; this one **refuses**. It is a Claude Code
`PreToolUse` hook, declared in your `settings.json`, and the agent runs it
before every command.

The four axes came from four real accidents, each with its number attached: 5
hooks deleted by a heredoc that closed early; a folder in `/tmp` that turned
out to be a clone of another project; a script that wrote inside someone
else's project while 4 write gates saw nothing; and 53 characters lost in a
file that came out valid UTF-8, exit 0, with no warning at all.

⚠️ The accented-search axis is the quietest of the four and the easiest to
underestimate: `grep` with an accent through the shell returns **0 matches for
text that is there**. It is not a bug that shows up — it is a false statement
wearing the clothes of a measurement.

### publishing: whatever leaves was measured before it left

| piece | what it does |
|---|---|
| `medir_privacidade.py` | finds private context in a file: person, company, internal project, disk path, dated incident, contact |
| `destilar.py` | prepares a piece for publication, and refuses whatever it could not clean |
| `vitrine.py` | renders a page with the state of the codebase |

🔴 `destilar` is the opposite of a sanitiser, and that is the whole point. A
silent sanitiser gives false confidence: it replaces what it knows, publishes
the rest, and whatever it did not know leaks quietly. Here it replaces only
the mechanical part (disk paths), measures its own output, and if one line
still carries private context it writes nothing. A line naming a client or an
incident is a judgement call, not a filter: a person writes the public
version, with the line in front of them.

This README and the pieces above went through it.

---

## Running it

No external dependencies. Python 3 and nothing else.

```bash
cp maquina/privacidade.json.exemplo maquina/privacidade.json
cp maquina/mapa.json.exemplo maquina/mapa.json
cp portas/casa.json.exemplo portas/casa.json
# open all three and put in your names, your accounts, your pieces

python maquina/inventario.py          # is the machine standing?
python maquina/o_basico.py            # does the codebase cover the basics?
python maquina/ligar_ci.py --todos    # who has tests no CI ever runs
python maquina/regua_de_trava.py <project-folder>
```

All three `.json` files are data, and the data is yours. Without them the
pieces stop with an error, on purpose: a detector that falls back to an empty
list approves everything in silence, an empty map answers "nothing broken"
about nothing at all, and a boundary that does not know where your work starts
answers "no owner" for every path — which the gates read as "go ahead and
write". Failing loudly is the choice, not an oversight.

The gate is a hook, so you wire it into Claude Code's `settings.json`:

```json
{ "hooks": { "PreToolUse": [ { "matcher": "Bash", "hooks": [
  { "type": "command",
    "command": "python \"/path/to/portas/bash_na_porta.py\"" } ] } ] } }
```

Read the piece before wiring it in. It will refuse commands of yours, and that
is precisely where its value is.

---

## The tests

```bash
python -B maquina/testar_inventario.py
python -B maquina/testar_o_basico.py
python -B maquina/testar_ligar_ci.py
python -B maquina/testar_consertar.py
python -B maquina/testar_vitrine.py
python -B maquina/testar_destilar.py
python -B maquina/testar_regua_de_trava.py
python -B maquina/testar_regua_de_complexidade.py
```

Measured: 9 suites, 199 checks, 28 mutations, 0 survivors.

In the codebase this came from it is 204. The 5 extra depend on things this
repository does not ship: a real codebase with projects in it, and one of the
gates, which lives in the agent's folder. They do not vanish quietly: the test
prints what it could not measure and why. A test that skips in silence becomes
decoration.

Every suite carries executable mutations, and that is what separates this from
a test set that merely passes. The question a green test does not answer is
"did it exercise the path?". A mutation answers it: break the target on
purpose and demand that the test catch it. If blinding the detector changes
nothing, the detector was not measuring anything.

The bar is stricter than "the test failed": the target must change and nothing
else. A coarse mutation that changes the whole world passes itself off as fine
detection by the very detector it was supposed to isolate.

---

## The boundary

These pieces measure and repair, and they touch projects that are not their
own. But committing and pushing in someone else's repository is theirs to do:
the piece prepares and shows, and you publish. Nothing here runs `git commit`
or `git push`.

---

## Where this came from

This repository is a distillation, not a parallel project. The pieces run
daily in a real codebase of about 30 projects. What you read here is the same
implementation, with the private context rewritten by hand, file by file, and
the result measured by `medir_privacidade` before it shipped.

There are not two implementations. Avoiding exactly that is why `destilar` was
written.

---

## Licence

MIT. See [LICENSE](LICENSE).
