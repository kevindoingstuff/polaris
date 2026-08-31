# polaris skills

Skills for [Claude Code](https://claude.com/claude-code). Each folder is one skill: a `SKILL.md` with YAML frontmatter and instructions, plus any supporting files.

| Skill | What it does | Invoke |
|---|---|---|
| [`commit`](commit/SKILL.md) | Writes the commit message in ASD-STE100 Simplified Technical English with the Conventional Commits format, splits unrelated changes into separate commits, then commits. | `/commit`, or say "commit this" |

## Install

Claude Code loads a skill from `~/.claude/skills/<name>/SKILL.md` (available in every project) or `<project>/.claude/skills/<name>/SKILL.md` (that project only).

**Option 1: copy one skill**

```bash
git clone https://github.com/kevindoingstuff/polaris.git
cp -r polaris/commit ~/.claude/skills/commit
```

**Option 2: clone once, link, and `git pull` to update**

macOS / Linux:

```bash
git clone https://github.com/kevindoingstuff/polaris.git ~/polaris-skills
ln -s ~/polaris-skills/commit ~/.claude/skills/commit
```

Windows (PowerShell, no admin needed):

```powershell
git clone https://github.com/kevindoingstuff/polaris.git $HOME\polaris-skills
New-Item -ItemType Junction -Path $HOME\.claude\skills\commit -Target $HOME\polaris-skills\commit
```

**Option 3: for one project only**

```bash
mkdir -p .claude/skills
cp -r polaris/commit .claude/skills/commit
```

Restart Claude Code after you install. Type `/` to see the skill in the list.

## Use

### commit

Make your changes, then:

```
> commit this
```

or

```
> /commit
```

The skill inspects the diff, stages the files that belong to the work (it leaves `.env` files and scratch output alone), splits a breaking change, a fix, a feature, and a dependency change into separate commits, and writes each message like this:

```
feat(config)!: replace the timeoutMs option with a timeout in seconds

The timeout option now takes seconds. The default value is 5.

The loader throws an error when a caller passes timeoutMs. This makes
sure that an old configuration does not run with the wrong unit.

BREAKING CHANGE: The timeoutMs option is removed. Use the timeout
option in seconds. For example, change timeoutMs: 5000 to timeout: 5.
```

The author is you. The skill adds no co-author or AI trailer.

## Update

```bash
cd ~/polaris-skills && git pull
```

With Option 1 or 3, copy the folder again.
