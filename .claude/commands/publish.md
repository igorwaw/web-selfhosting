Publish the post at `content/$ARGUMENTS/index.md`. Do all of the following steps:

1. **Remove draft status** — delete the `draft: true` line from the front matter.

2. **Set today's date** — add or replace the `date:` field in the front matter with today's date and time in the format `YYYY-MM-DDTHH:MM:SS` (use noon, e.g. `2026-07-04T12:00:00`).

3. **Place photos** — list all files in `content/posts/$ARGUMENTS/`. For each image file (jpg, jpeg, png, webp, svg) except `1.jpg` (always skip it), decide where in the post body it fits best based solely on the filename — do not open or analyse the image. Match the filename to the nearest relevant section or paragraph. If you are unsure where a photo belongs, place it at the very beginning of the post body (before the first paragraph). Insert each photo as `![](filename)` on its own line with a blank line before and after.

4. **Rebuild** — run `hugo --cleanDestinationDir` and report the result.
