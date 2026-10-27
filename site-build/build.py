#!/usr/bin/env python3
"""Build the Carol Townsend fan site (static HTML) from the archive in ../posts.

Output: ../site/  (plain static files; GitHub Pages or Cloudflare Pages can serve it as-is).
Newest post first, like the old Blogspot/Squarespace blogs.
Usage: python3 build.py
"""
import datetime
import glob
import html
import os
import re
import shutil

import markdown

ARCH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ARCH, "docs")
PER_PAGE = 10
CONTACT_URL = "https://script.google.com/macros/s/AKfycbzu6kdYVUPhYrNXcghPL_aZRmjJNCIauRQs4B1erO9ykOy9F_TE07WOppQx5_FrtdRi/exec"
SITE_NAME = "Carol Townsend Fan Site"
TAGLINE = "Your first stop for all things relating to Carol Townsend's meteoric rise to stardom"


def parse_post(path):
    raw = open(path, encoding="utf-8").read()
    _, fm, body = raw.split("---\n", 2)
    meta = {}
    for line in fm.strip().split("\n"):
        k, v = line.split(": ", 1)
        meta[k] = v.strip().strip('"')
    stem = os.path.splitext(os.path.basename(path))[0]
    num = int(stem.split("-", 1)[0])
    slug = stem  # unique per file (two posts share a title/date)
    comments = []
    if "## Comments" in body:
        body, ctext = body.split("## Comments", 1)
        for a, d, q in re.findall(r"\*\*(.+?)\*\* — \*(.+?)\*\n\n((?:> .*\n?)+)", ctext):
            text = " ".join(l[2:] for l in q.strip().split("\n"))
            comments.append((a, d, text))
    body = body.replace("---\n", "").strip()
    # strip the title H1 and the "Originally published" line; we render our own
    body = re.sub(r"^# .*\n", "", body, count=1).strip()
    body = re.sub(r"^\*Originally published.*\*\n?", "", body, count=1).strip()
    body = body.replace("](../images/", "](images/")  # rewritten below per depth
    return dict(
        num=num, slug=slug, title=meta["title"], date=meta["date"],
        source=meta.get("source", ""), body=body, comments=comments,
        original=meta.get("original_url", ""),
        missing=int(meta.get("images_missing", 0)),
    )


def md_to_html(text, depth):
    prefix = "../" * depth
    text = text.replace("](images/", f"]({prefix}images/")
    out = markdown.markdown(text, extensions=["extra"])
    # plain (non-image) missing markers are blockquotes; leave them as-is
    return out


def fdate(d):
    return datetime.date.fromisoformat(d).strftime("%B %-d, %Y")


def excerpt(text, n=220):
    plain = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", plain)
    plain = re.sub(r"[*>#_`]", "", plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    return (plain[:n].rsplit(" ", 1)[0] + "…") if len(plain) > n else plain


def first_image(text):
    m = re.search(r"!\[.*?\]\(images/([^)]+)\)", text)
    return m.group(1) if m else None


def page(depth, title, body, active):
    root = "../" * depth
    nav = [("index.html", "Home"), ("archive.html", "Archive"), ("gallery.html", "Photo Gallery"),
           ("about.html", "About Carol"), ("contact.html", "Contact")]
    links = "".join(
        f'<a href="{root}{href}"{" class=on" if href == active else ""}>{label}</a>'
        for href, label in nav)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · {SITE_NAME}</title>
<link rel="stylesheet" href="{root}style.css"></head>
<body>
<header><h1><a href="{root}index.html">Carol Townsend</a></h1>
<p>Stage, screen, and the occasional crowd scene</p></header>
<nav>{links}</nav>
<main>{body}</main>
<footer>{SITE_NAME} · Posts and comments restored from the original Blogspot (2006–2014) and Squarespace (2014–2017) sites</footer>
</body></html>
"""


def post_html(p, depth):
    body = md_to_html(p["body"], depth)
    coms = ""
    if p["comments"]:
        items = "".join(
            f'<div class="c"><b>{html.escape(a)}</b> <span>{html.escape(d)}</span>'
            f'<p>{html.escape(t)}</p></div>' for a, d, t in p["comments"])
        coms = (f'<section class="coms"><h3>Comments ({len(p["comments"])})</h3>'
                f'<p class="small">Archived from the original site.</p>{items}</section>')
    src = {"blogger": "Originally published on the Blogspot site",
           "squarespace": "Originally published on caroltownsend.com"}.get(p["source"], "")
    return f"""<article class="post">
<a class="back" href="{'../' * depth}index.html">← All posts</a>
<div class="meta">{fdate(p['date'])}</div>
<h1>{html.escape(p['title'])}</h1>
<div class="body">{body}</div>
<p class="small src">{src}</p>
{coms}
</article>"""


def card(p, depth):
    img = first_image(p["body"])
    root = "../" * depth
    thumb = (f'<img src="{root}images/{img}" alt="" loading="lazy">' if img
             else '<div class="noimg"><span>CT</span></div>')
    n = len(p["comments"])
    ctext = f'{n} comment{"s" if n != 1 else ""}' if n else ""
    return f"""<a class="card" href="{root}posts/{p['slug']}.html">{thumb}
<div><div class="meta">{fdate(p['date'])}</div><h2>{html.escape(p['title'])}</h2>
<p>{html.escape(excerpt(p['body']))}</p><span class="small">{ctext}</span></div></a>"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    posts = [parse_post(p) for p in glob.glob(os.path.join(ARCH, "posts", "*.md"))]
    posts.sort(key=lambda p: (p["date"], p["num"]), reverse=True)  # newest first
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(ARCH, "images"), os.path.join(OUT, "images"))
    shutil.copytree(os.path.join(ARCH, "gallery"), os.path.join(OUT, "gallery"),
                    ignore=shutil.ignore_patterns("*.md"))
    shutil.copy(os.path.join(os.path.dirname(__file__), "style.css"), OUT)

    # individual post pages
    for p in posts:
        write(os.path.join(OUT, "posts", p["slug"] + ".html"),
              page(1, p["title"], post_html(p, 1), ""))

    # paginated home (newest first)
    pages = [posts[i:i + PER_PAGE] for i in range(0, len(posts), PER_PAGE)]
    for i, chunk in enumerate(pages, start=1):
        cards = "".join(card(p, 0) for p in chunk)
        nav = []
        if i > 1:
            nav.append(f'<a href="{"index.html" if i == 2 else f"page-{i-1}.html"}">← Newer posts</a>')
        if i < len(pages):
            nav.append(f'<a href="page-{i+1}.html">Older posts →</a>')
        body = (f'<div class="meta">Latest posts · {len(posts)} in all</div>{cards}'
                f'<div class="pager">{" &nbsp; ".join(nav)}</div>')
        out = page(0, "Home", body, "")
        write(os.path.join(OUT, "index.html" if i == 1 else f"page-{i}.html"), out)

    # archive by year (newest year first)
    by_year = {}
    for p in posts:
        by_year.setdefault(p["date"][:4], []).append(p)
    rows = []
    for y in sorted(by_year, reverse=True):
        items = "".join(f'<li><span class="small">{fdate(p["date"])}</span> '
                        f'<a href="posts/{p["slug"]}.html">{html.escape(p["title"])}</a></li>'
                        for p in by_year[y])
        rows.append(f"<h2>{y} <span class='small'>({len(by_year[y])})</span></h2><ul class='arch'>{items}</ul>")
    write(os.path.join(OUT, "archive.html"),
          page(0, "Archive", f'<h1>Archive</h1><p>{len(posts)} posts, newest first.</p>' + "".join(rows), "archive.html"))

    # gallery
    gfiles = sorted(f for f in os.listdir(os.path.join(ARCH, "gallery"))
                    if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif")))
    tiles = "".join(f'<a href="gallery/{f}"><img src="gallery/{f}" alt="" loading="lazy"></a>' for f in gfiles)
    write(os.path.join(OUT, "gallery.html"),
          page(0, "Photo Gallery", f'<h1>Photo Gallery</h1><p class="small">{len(gfiles)} photos, full size.</p><div class="grid">{tiles}</div>', "gallery.html"))

    # about (from the archived About page)
    about_src = open(os.path.join(ARCH, "site-pages", "ABOUT.md"), encoding="utf-8").read()
    lines = [l.strip() for l in about_src.split("\n")]
    start = lines.index("Carol Townsend") + 1
    end = next(i for i, l in enumerate(lines) if l.startswith("This site is all about"))
    paras = [re.sub(r"\s+", " ", l) for l in lines[start:end] if l]
    paras = [p.replace(" .", ".").replace(" ,", ",") for p in paras]
    about_html = "".join(f"<p>{html.escape(p)}</p>" for p in paras)
    write(os.path.join(OUT, "about.html"),
          page(0, "About Carol", f'<h1>About Carol</h1>{about_html}<p><em>Who am I? I\'m her biggest fan!</em></p>', "about.html"))

    # contact form -> Google Apps Script -> private Google Sheet (+ email to owner)
    form = """<h1>Contact</h1>
<p>Want to say hello to Carol, ask about a show, or share a memory? Send a note below.</p>
<form id="cf" class="cform">
<label>Your name <span class="small">(optional)</span><input name="name" maxlength="100" autocomplete="name"></label>
<label>Your email <span class="small">(optional, only if you'd like a reply)</span><input name="email" type="email" maxlength="150" autocomplete="email"></label>
<label>Message<textarea name="message" rows="7" maxlength="3000" required></textarea></label>
<div class="hp" aria-hidden="true"><label>Leave this empty<input name="website" tabindex="-1" autocomplete="off"></label></div>
<button type="submit">Send message</button>
<p id="cf-status" class="small" role="status"></p>
</form>
<script>
(function(){
var URL="__CONTACT_URL__",t0=Date.now(),f=document.getElementById("cf"),st=document.getElementById("cf-status"),b=f.querySelector("button");
f.addEventListener("submit",function(e){
 e.preventDefault();b.disabled=true;st.textContent="Sending…";
 var d=new URLSearchParams(new FormData(f));d.set("elapsed",String(Date.now()-t0));
 fetch(URL,{method:"POST",body:d}).then(function(r){return r.json()}).then(function(j){
  if(j.status==="ok"){f.reset();st.textContent="Thank you! Your message was sent.";}
  else{st.textContent=j.message||"Sorry, something went wrong. Please try again.";b.disabled=false;}
 }).catch(function(){st.textContent="Sorry, that didn't go through. Please try again in a bit.";b.disabled=false;});
});
})();
</script>""".replace("__CONTACT_URL__", CONTACT_URL)
    write(os.path.join(OUT, "contact.html"), page(0, "Contact", form, "contact.html"))

    print(f"posts={len(posts)} home_pages={len(pages)} years={len(by_year)} gallery={len(gfiles)}")


if __name__ == "__main__":
    main()
