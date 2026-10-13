# -*- coding: utf-8 -*-
"""Import only userid/name from an existing local WIKI contacts snapshot. No network."""
import argparse, hashlib, json, re
from pathlib import Path

def contacts_map(source):
    text = source.read_text(encoding='utf-8')
    header = re.match(r'^---\n(.*?)\n---', text, re.S)
    if not header or not re.search(r'^type: [\"\']?contacts', header.group(1), re.M):
        raise ValueError('Expected a WIKI contacts snapshot')
    date = re.search(r'^date: [\"\']?(\d{4}-\d{2}-\d{2})', header.group(1), re.M)
    fetched = re.search(r'^fetched_at: (.+)$', header.group(1), re.M)
    if not date:
        raise ValueError('Snapshot date missing')
    users = {}
    def visit(value):
        if isinstance(value, dict):
            userid, name = value.get('userid'), value.get('name')
            if isinstance(userid, str) and isinstance(name, str) and userid.strip() and name.strip():
                userid, name = userid.strip(), name.strip()
                if userid in users and users[userid] != name:
                    raise ValueError('Conflicting names for the same userid; review required')
                users[userid] = name
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    for block in re.findall(r'```json\s*\n(.*?)```', text, re.S):
        visit(json.loads(block))
    expected = re.search(r'^count: [\"\']?(\d+)', header.group(1), re.M)
    if not users or expected and len(users) != int(expected.group(1)):
        raise ValueError('Incomplete contacts snapshot; keep the previous map')
    return {'snapshotDate': date.group(1), 'fetchedAt': fetched.group(1).strip('\"\'') if fetched else '',
            'source': str(source), 'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'users': dict(sorted(users.items()))}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(json.loads((Path(__file__).resolve().parents[1]/'config.json').read_text()).get('wiki_root','inputs/wiki'))/'wecom/contacts/current.md')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'local-site/lib/wecom-users.json')
    args = parser.parse_args()
    data = contacts_map(args.source)
    content = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + '.tmp')
    temp.write_text(content, encoding='utf-8')
    temp.replace(args.output)
    print(json.dumps({'snapshotDate': data['snapshotDate'], 'members': len(data['users'])}, ensure_ascii=False))
