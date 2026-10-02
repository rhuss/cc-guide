#!/usr/bin/env bash
# Probe the superpowers contract that cc-guide relies on (FR-004).
#   usage: superpowers-probe.sh
# Reads $HOME/.claude/plugins/installed_plugins.json, checks the required skills
# and scripts listed in ../compat.yaml, and prints JSON:
#   {installPath, version, known, ok, problems[]}
# Exit status: 0 ok, 3 ok but the version is not in compat.yaml, 4 probe failed
# (including superpowers not installed).
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
compat="$here/../compat.yaml"
registry="${HOME}/.claude/plugins/installed_plugins.json"
problems=()

have_jq() { [[ -z "${CC_GUIDE_NO_JQ:-}" ]] && command -v jq >/dev/null 2>&1; }

# compat_list <key>: the "- item" lines under <key>: in compat.yaml
compat_list() {
  awk -v key="$1" '
    $0 ~ "^" key ":" { inlist = 1; next }
    /^[^ #-]/ { inlist = 0 }
    inlist && /^[ ]*-[ ]/ { sub(/^[ ]*-[ ]*/, ""); gsub(/["\047]/, ""); sub(/[ ]*#.*$/, ""); print }
  ' "$compat"
}

# registry_entry: "<installPath>\t<version>" of the superpowers entry, user scope first
registry_entry() {
  if have_jq; then
    jq -r '
      [ (.plugins // {}) | to_entries[] | select(.key | startswith("superpowers@"))
        | .value | if type == "array" then .[] else . end ]
      | (map(select(.scope == "user")) + map(select(.scope != "user")))
      | first // empty
      | [(.installPath // ""), (.version // "")] | @tsv
    ' "$registry" 2>/dev/null
  else
    python3 - "$registry" <<'PY' 2>/dev/null
import json, sys
data = json.load(open(sys.argv[1]))
entries = []
for key, value in (data.get("plugins") or {}).items():
    if key.startswith("superpowers@"):
        entries.extend(value if isinstance(value, list) else [value])
entries.sort(key=lambda e: e.get("scope") != "user")
if entries:
    print(f"{entries[0].get('installPath') or ''}\t{entries[0].get('version') or ''}")
PY
  fi
}

# emit <installPath> <version> <known> <ok>: print the JSON result
emit() {
  if have_jq; then
    { [[ ${#problems[@]} -gt 0 ]] && printf '%s\n' "${problems[@]}"; } | jq -R . | jq -s \
      --arg ip "$1" --arg v "$2" --argjson known "$3" --argjson ok "$4" \
      '{installPath: (if $ip == "" then null else $ip end),
        version: (if $v == "" then null else $v end),
        known: $known, ok: $ok, problems: .}'
  else
    python3 - "$1" "$2" "$3" "$4" ${problems[@]+"${problems[@]}"} <<'PY'
import json, sys
ip, v, known, ok = sys.argv[1:5]
print(json.dumps({"installPath": ip or None, "version": v or None, "known": known == "true",
                  "ok": ok == "true", "problems": sys.argv[5:]}, indent=2))
PY
  fi
}

install_path=""
version=""
if [[ ! -f "$compat" ]]; then
  problems+=("compat.yaml not found next to the plugin scripts: $compat")
fi
if [[ ! -f "$registry" ]]; then
  problems+=("superpowers is not installed (no $registry); install it with: claude plugin install superpowers@claude-plugins-official")
else
  entry=$(registry_entry)
  if [[ -z "$entry" ]]; then
    problems+=("superpowers is not installed; install it with: claude plugin install superpowers@claude-plugins-official")
  else
    install_path=${entry%%$'\t'*}
    version=${entry#*$'\t'}
  fi
fi

if [[ -n "$install_path" && ! -d "$install_path" ]]; then
  problems+=("superpowers installPath does not exist: $install_path (reinstall the plugin)")
elif [[ -n "$install_path" && -f "$compat" ]]; then
  if [[ -z "$version" && -f "$install_path/.claude-plugin/plugin.json" ]]; then
    version=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$install_path/.claude-plugin/plugin.json" | head -1)
  fi
  while IFS= read -r skill; do
    [[ -z "$skill" ]] && continue
    [[ -f "$install_path/skills/$skill/SKILL.md" ]] || problems+=("missing skill: skills/$skill/SKILL.md")
  done < <(compat_list required_skills)
  scripts_dir="$install_path/skills/subagent-driven-development/scripts"
  while IFS= read -r script; do
    [[ -z "$script" ]] && continue
    if [[ ! -f "$scripts_dir/$script" ]]; then
      problems+=("missing script: skills/subagent-driven-development/scripts/$script")
      continue
    fi
    out=$(bash "$scripts_dir/$script" </dev/null 2>&1)
    status=$?
    if [[ $status -ne 2 ]]; then
      problems+=("script $script without arguments exited $status, expected 2 (contract changed?)")
    elif ! grep -q '^usage:' <<<"$out"; then
      problems+=("script $script printed no 'usage:' line (contract changed?)")
    fi
  done < <(compat_list required_scripts)
fi

known=false
if [[ -n "$version" && -f "$compat" ]] && compat_list known_good | grep -qxF "$version"; then
  known=true
fi

# Versions older than minimum_version fail (scripts and ledger semantics changed in 6.3.0).
minimum=$(sed -n 's/^minimum_version:[[:space:]]*"\{0,1\}\([0-9.]*\)"\{0,1\}.*/\1/p' "$compat" 2>/dev/null | head -1)
if [[ -n "$version" && -n "$minimum" ]] && ! awk -v a="$version" -v b="$minimum" 'BEGIN {
    n = split(a, x, "."); m = split(b, y, ".");
    for (i = 1; i <= (n > m ? n : m); i++) { if ((x[i] + 0) > (y[i] + 0)) exit 0; if ((x[i] + 0) < (y[i] + 0)) exit 1 }
    exit 0 }'; then
  problems+=("superpowers $version is older than the minimum $minimum; update it with: claude plugin update superpowers@claude-plugins-official")
fi

if [[ ${#problems[@]} -gt 0 ]]; then
  emit "$install_path" "$version" "$known" false
  exit 4
fi
emit "$install_path" "$version" "$known" true
[[ "$known" == true ]] && exit 0
exit 3
