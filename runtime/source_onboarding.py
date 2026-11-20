"""Bounded, evidence-labeled, source-first project onboarding.

Only explicitly supplied HTTPS URLs, owned local files and user-uploaded documents.
No credentials, private Drive bypasses, site crawling or automatic source execution.
"""
from __future__ import annotations
import html
import base64
import csv
import io
import os
import shutil
import subprocess
from html.parser import HTMLParser
import http.client
import ipaddress
import json
import re
import socket
from ssl import create_default_context
from urllib.parse import urlsplit, quote, urlencode, urljoin
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

MAX_REMOTE = 240000
MAX_EXTRACT = 22000
FIELDS = ("name", "region", "goal", "audience", "website", "successMeasure", "notes")
LABELS = {
    "name": "name", "company name": "name", "brand": "name", "project": "name",
    "region": "region", "country": "region", "location": "region",
    "goal": "goal", "business goal": "goal", "objective": "goal",
    "audience": "audience", "target audience": "audience", "target customer": "audience",
    "target users": "audience", "ideal customer": "audience",
    "website": "website", "homepage": "website",
    "success measure": "successMeasure", "measure of success": "successMeasure",
    "primary metric": "successMeasure", "kpi": "successMeasure",
}
class SourceError(ValueError):
    pass

class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.title = []
        self.description = ""
        self._skip = 0
        self._in_title = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style", "svg", "noscript"):
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta" and attrs.get("name","").lower() == "description":
            self.description = attrs.get("content","")[:450]
        if tag in ("p", "h1", "h2", "h3", "li", "br", "div", "section"):
            self.text.append("\n")
    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg", "noscript"):
            self._skip = max(0, self._skip - 1)
        if tag == "title":
            self._in_title = False
    def handle_data(self, data):
        if not self._skip:
            self.text.append(data)
            if self._in_title:
                self.title.append(data)

def _public_address(host):
    try:
        addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
    except OSError as e:
        raise SourceError("Could not resolve the source host") from e
    ips={row[4][0] for row in addresses}
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise SourceError("Private, local or non-public source address blocked")
    return sorted(ips)[0]

def _remote(url, allowed_hosts=None, headers=None, redirects=0):
    if not isinstance(url,str) or len(url)>1400:
        raise SourceError("Invalid source URL")
    parsed=urlsplit(url)
    if (parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.port not in (None,443) or parsed.fragment):
        raise SourceError("Only public HTTPS URLs on port 443 are supported")
    host=parsed.hostname.encode("idna").decode("ascii").lower()
    if allowed_hosts and host not in allowed_hosts:
        raise SourceError("Source host does not match the expected provider")
    ip=_public_address(host)
    conn=http.client.HTTPSConnection(host,443,timeout=8,context=create_default_context())
    # Pin the connection to the validated public IP, retaining TLS hostname validation.
    conn._create_connection=lambda address,timeout=None,source_address=None: socket.create_connection((ip,443),timeout=timeout)
    try:
        path=parsed.path or "/"
        if parsed.query:path+="?"+parsed.query
        conn.request("GET",path,headers={"Accept":"text/html,text/plain,application/json","User-Agent":"AIBO-Source-Preview/1",**(headers or {})})
        response=conn.getresponse()
        if not 200<=response.status<300:
            if 300<=response.status<400 and redirects<2:
                target=urljoin(url,response.getheader("Location",""))
                next_host=(urlsplit(target).hostname or "").lower()
                if allowed_hosts and next_host not in allowed_hosts and not (
                        "docs.google.com" in allowed_hosts and
                        (next_host=="googleusercontent.com" or next_host.endswith(".googleusercontent.com"))):
                    raise SourceError("Source redirected outside its approved host")
                return _remote(target,allowed_hosts if next_host in (allowed_hosts or ()) else None,
                               headers if next_host in (allowed_hosts or ()) else None,redirects+1)
            if 300<=response.status<400:
                raise SourceError("Source redirects were blocked")
            raise SourceError("Source unavailable (HTTP "+str(response.status)+"); check sharing permissions")
        kind=response.getheader("Content-Type","").lower()
        if not any(x in kind for x in ("text/", "application/json", "application/xml", "application/xhtml+xml")):
            raise SourceError("Source does not provide readable text; upload the document instead")
        data=response.read(MAX_REMOTE+1)
        if len(data)>MAX_REMOTE:
            raise SourceError("Source exceeds safe preview size")
        return data.decode("utf-8-sig",errors="replace")
    except (OSError,ValueError,http.client.HTTPException) as e:
        if isinstance(e,SourceError):raise
        raise SourceError("Unable to inspect source over HTTPS") from e
    finally:
        conn.close()

def _unpack_text(data,ext):
    try:
        if ext in (".md",".txt",".csv",".json"):
            return data[:MAX_EXTRACT].decode("utf-8-sig",errors="replace")
        if ext in (".docx",".xlsx",".pptx"):
            with zipfile.ZipFile(__import__("io").BytesIO(data)) as bundle:
                names=bundle.namelist()
                expected={"docx":lambda n:n=="word/document.xml",
                          "xlsx":lambda n:n.startswith("xl/worksheets/sheet") or n=="xl/sharedStrings.xml",
                          "pptx":lambda n:n.startswith("ppt/slides/slide")}[ext[1:]]
                parts=[]
                for name in names:
                    if not expected(name):continue
                    if bundle.getinfo(name).file_size>1500000:continue
                    element=ET.fromstring(bundle.read(name))
                    if ext==".docx":
                        paras=[node for node in element.iter() if node.tag.endswith("}p")]
                        blocks=["".join((child.text or "") for child in p.iter() if child.tag.endswith("}t"))
                                for p in paras]
                        parts.extend(x for x in blocks if x.strip())
                    elif ext==".pptx":
                        blocks=["".join((child.text or "") for child in p.iter() if child.tag.endswith("}t"))
                                for p in element.iter() if p.tag.endswith("}p")]
                        parts.extend(x for x in blocks if x.strip())
                    else:
                        parts.extend(x.text for x in element.iter() if x.text and x.tag.endswith(("}t","}v")))
                    if sum(map(len,parts))>=MAX_EXTRACT:break
                return "\n".join(parts)[:MAX_EXTRACT]
        if ext==".pdf":
            try:
                from pypdf import PdfReader
            except ImportError as e:
                raise SourceError("PDF text extraction unavailable in this installation; provide TXT/DOCX or install pypdf") from e
            reader=PdfReader(__import__("io").BytesIO(data),strict=False)
            return "\n".join((page.extract_text() or "") for page in reader.pages[:12])[:MAX_EXTRACT]
    except (zipfile.BadZipFile,ET.ParseError,KeyError,ValueError) as e:
        raise SourceError("Document could not be read") from e
    raise SourceError("Unsupported document type")

def _extract(label,content,is_html=False,website=""):
    title=""
    desc=""
    if is_html:
        parser=PageText()
        parser.feed(content[:MAX_REMOTE])
        title=" ".join(parser.title).strip()[:160]
        desc=parser.description.strip()
        content="".join(parser.text)
    clean=html.unescape(re.sub(r"\r","\n",content))[:MAX_EXTRACT]
    # Never preserve credential-shaped lines in source excerpts passed to Soni.
    clean="\n".join(line for line in clean.split("\n")
                    if not re.search(r"(?i)(?:api[_ -]?key|password|client_secret|access_token|private[_ -]?key|authorization\s*:)",line))
    lines=[re.sub(r"\s+"," ",x).strip(" #\t") for x in clean.split("\n")]
    # Normalize common business-brief markdown: **Goal:** and headings.
    lines=[re.sub(r"^\*{1,2}([^*]+)\*{1,2}\s*:",r"\1:",line) for line in lines]
    evidence=[]
    for i,line in enumerate(lines):
        match=re.match(r"^([A-Za-z][\w /-]{2,30}):\s*(.{4,400})$",line)
        if match:
            key=LABELS.get(match.group(1).casefold().strip())
            if key:
                evidence.append({"field":key,"value":match.group(2)[:400],"source":label,"confidence":"explicit"})
            continue
        # Documents commonly give a heading and explanation on separate lines.
        heading=re.sub(r"^\*{1,2}(.+?)\*{1,2}$",r"\1",line).strip().rstrip(":")
        key=LABELS.get(heading.casefold())
        if not key:continue
        following=next((candidate for candidate in lines[i+1:i+4] if candidate), "")
        if 4<=len(following)<=400 and not LABELS.get(following.lower().rstrip(":")):
            evidence.append({"field":key,"value":following,"source":label,"confidence":"explicit-heading"})
    if website:
        evidence.append({"field":"website","value":website,"source":label,"confidence":"explicit"})
    if title:
        evidence.append({"field":"description","value":title,"source":label,"confidence":"context"})
    if desc:
        evidence.append({"field":"description","value":desc,"source":label,"confidence":"context"})
    return {"reference":label,"evidence":evidence[:50],"excerpt":clean[:1800],"read":True}

def _github_token():
    token=os.environ.get("GITHUB_TOKEN","").strip()
    if token:return token
    if not shutil.which("gh"):return ""
    try:
        result=subprocess.run(["gh","auth","token"],capture_output=True,text=True,timeout=4,check=False)
        if result.returncode==0:return result.stdout.strip()[:2048]
    except (OSError,subprocess.TimeoutExpired):
        pass
    return ""

def inspect_remote(kind,raw_url,drive_token=None):
    if not raw_url:return None
    parsed=urlsplit(raw_url)
    host=(parsed.hostname or "").lower()
    if kind=="website":
        contents=_remote(raw_url)
        return _extract(raw_url,contents,True,raw_url)
    if kind=="repository":
        if host!="github.com":raise SourceError("Enter a github.com/owner/repository URL")
        match=re.fullmatch(r"/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?",parsed.path)
        if not match:raise SourceError("Enter a GitHub repository homepage URL")
        owner,name=match.groups()
        endpoint="https://api.github.com/repos/"+quote(owner)+"/"+quote(name)+"/readme"
        token=_github_token()
        headers={"Authorization":"Bearer "+token} if token else None
        contents=_remote(endpoint,{"api.github.com"},headers=headers)
        try:
            data=json.loads(contents)
            if data.get("encoding")!="base64":raise SourceError("GitHub README has no readable content")
            contents=base64.b64decode(data["content"],validate=False).decode("utf-8-sig",errors="replace")
        except (KeyError,TypeError,ValueError) as exc:
            raise SourceError("GitHub README could not be decoded") from exc
        return _extract(raw_url+" · README",contents)
    if kind=="drive":
        if host not in ("docs.google.com","drive.google.com"):
            raise SourceError("Enter a Google Docs or public Drive link")
        match=re.fullmatch(r"/document/d/([A-Za-z0-9_-]{10,})/?.*",parsed.path)
        if host=="docs.google.com" and match:
            doc_id=match.group(1)
            token=drive_token or os.environ.get("GOOGLE_DRIVE_ACCESS_TOKEN","").strip()
            if token:
                endpoint="https://www.googleapis.com/drive/v3/files/"+doc_id+"/export?mimeType=text%2Fplain"
                return _extract(raw_url,_remote(endpoint,{"www.googleapis.com"},
                                headers={"Authorization":"Bearer "+token}))
            endpoint="https://docs.google.com/document/d/"+doc_id+"/export?format=txt"
            return _extract(raw_url,_remote(endpoint,{"docs.google.com"}))
        folder=re.fullmatch(r"/drive/folders/([A-Za-z0-9_-]{10,})/?",parsed.path)
        if host=="drive.google.com" and folder:
            token=drive_token or os.environ.get("GOOGLE_DRIVE_ACCESS_TOKEN","").strip()
            if not token:
                raise SourceError("Private Drive folder requires a connected Google Drive account or exported file uploads")
            folder_id=folder.group(1)
            query=urlencode({"q":"'"+folder_id+"' in parents and trashed = false",
                             "fields":"files(id,name,mimeType),nextPageToken","pageSize":"8"})
            endpoint="https://www.googleapis.com/drive/v3/files?"+query
            headers={"Authorization":"Bearer "+token}
            data=json.loads(_remote(endpoint,{"www.googleapis.com"},headers=headers))
            found=[]
            for item in data.get("files",[]):
                if item.get("mimeType")!="application/vnd.google-apps.document":continue
                doc_id=item.get("id","")
                if not re.fullmatch(r"[A-Za-z0-9_-]{10,}",doc_id):continue
                target="https://www.googleapis.com/drive/v3/files/"+doc_id+"/export?mimeType=text%2Fplain"
                try:found.append(_extract(raw_url+" · "+item.get("name","Google Doc"),
                                          _remote(target,{"www.googleapis.com"},headers=headers)))
                except SourceError:continue
                if len(found)>=5:break
            if not found:raise SourceError("No readable Google Docs found in the accessible Drive folder")
            return found
        raise SourceError("Google Drive source requires a readable Google Doc or authenticated folder access")
    raise SourceError("Unsupported source type")

def inspect_document(filename,raw):
    ext=Path(filename).suffix.lower()
    contents=_unpack_text(raw,ext)
    if not contents.strip():
        raise SourceError("Document contains no extractable text")
    item=_extract("Uploaded document · "+Path(filename).name,contents)
    if ext==".json":
        try:
            data=json.loads(contents)
            objects=[data] if isinstance(data,dict) else []
            for obj in objects:
                for key,value in list(obj.items())[:100]:
                    field=LABELS.get(str(key).replace("_"," ").replace("-"," ").lower())
                    if field and isinstance(value,(str,int,float)) and 4<=len(str(value))<=400:
                        item["evidence"].append({"field":field,"value":str(value),
                                                 "source":item["reference"],"confidence":"explicit"})
        except (ValueError,TypeError):pass
    elif ext==".csv":
        try:
            rows=iter(csv.reader(io.StringIO(contents)))
            headers=next(rows,[])
            first=next(rows,[])
            for key,value in zip(headers,first):
                field=LABELS.get(key.strip().replace("_"," ").lower())
                if field and 4<=len(value)<=400:
                    item["evidence"].append({"field":field,"value":value.strip(),
                                             "source":item["reference"],"confidence":"explicit"})
        except (ValueError,csv.Error,StopIteration):pass
    return item

def consolidate(evidence):
    proposed={}
    conflicts={}
    for source in evidence:
        for item in source.get("evidence",[]):
            key=item["field"]
            if key not in FIELDS:continue
            if key not in proposed:
                proposed[key]={"value":item["value"],"source":item["source"],
                               "confidence":item["confidence"]}
            elif proposed[key]["value"].casefold()!=item["value"].casefold():
                conflicts.setdefault(key,[]).append({"value":item["value"],"source":item["source"]})
    return {"suggestions":proposed,"conflicts":conflicts}
