# tools/ — build helpers (DEV ONLY)

> ⚠️ **Delete this `tools/` folder before publishing the site.**
> These are build-time helpers, not part of the website. They must not be
> deployed or served publicly.

## build_blog.py

Generates the Članki section from the source posts on the old live WordPress
site:

- `clanki.html` — the article index (media-row list)
- `clanki/<slug>.html` — one page per article (28 total)
- `img/blog/` — article images (decoded from the source / downloaded)

Run it from the repo root after changing shared markup (nav / footer / cookie)
or the article template/CSS, so all pages stay consistent:

```bash
python3 tools/build_blog.py
```

It re-downloads the source posts from `https://www.nemo.si`, so it only works
**while the old WordPress blog is still live**. After launch the old blog is
gone and this script can no longer fetch sources — another reason to remove
`tools/` at publish time.

Requires only Python 3 standard library (no pip installs).
