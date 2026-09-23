# Publication and privacy

The project targets [TTSKY26d](https://app.tinytapeout.com/shuttles/ttsky26d).
Public attribution uses the GitHub handle `qd39l`, including the existing
`tt_um_qd39l_echoscope` module name. The repository intentionally links to that
public identity. Commit email addresses use GitHub's noreply service.

Before publishing, run `make privacy`. It checks tracked files, non-ignored
new files, branch/tag/remote Git blobs, and commit identities for common personal
paths, private network addresses, emails, credential formats, and local files.
The same check runs in CI with full history. It reports locations and rule
names without printing potential secret values. This is a heuristic check;
review new prose, screenshots, image metadata, and unfamiliar token formats
manually. It does not inspect ignored local files or guarantee anonymity.

Keep local notes, credentials, raw logs, tool checkouts, runs, and private
backups ignored. Push the Git repository rather than uploading a ZIP of the
working directory. Publish ordinary branches and tags, never `git push --mirror`:
local app snapshot refs and reflogs can retain private recovery data and are
outside this check's publication scope. `.gitignore` does not protect files already committed or
files added with `git add -f`. Removing a leak from the latest tree does not
remove it from earlier commits or tags. Repository-local Git identity settings
do not transfer to a new clone; configure the intended public identity there.

The initial prepublication review covered source, documentation, workflows,
saved verification reports, both PNGs and their metadata, the local submission
package, and the single initial commit. No credentials or host-specific paths
were found in those publishable artifacts. Public attribution replaced the
real-name author field and initial commit identity. The original commit is
preserved only in an ignored local backup, outside publishable Git refs.
The design, experiments, results, and local build outputs are preserved.

Container paths such as `/work` and `/pdk`, relative project paths, localhost
demo URLs, and example PDK paths are intentional. Packaging accepts only
credential-free GitHub origin URLs and checks package contents for common
leaks before creating the archive. GitHub SSH origins are converted to HTTPS.

## Existing physical evidence

The attribution-only change in `info.yaml` did not change RTL, pinout, timing,
or physical configuration. `verification/metadata-update.json` records the
exact original and public metadata hashes; parsed YAML was compared with only
`project.author` removed. Original build hashes remain unchanged. Evidence
collection and packaging accept this exact recorded pair while continuing to
reject any other changed build input. Package provenance records both the
original build inputs and current packaging inputs. Future physical builds
will naturally record the updated metadata hash.

Publishing on GitHub and submitting to the shuttle remain separate steps.
