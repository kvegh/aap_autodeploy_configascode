"""Validate GoDaddy v3 DNS pages without performing network operations."""
from collections.abc import Mapping
from ipaddress import IPv4Address
import re
from ansible.errors import AnsibleFilterError


def godaddy_v3_records(page, name=None, record_type=None, complete=True):
    """Reject malformed, truncated or differently filtered provider responses."""
    def reject():
        raise AnsibleFilterError('Invalid or incomplete GoDaddy v3 DNS response')
    if not isinstance(page, Mapping) or not isinstance(page.get('items'), list):
        reject()
    records = page['items']
    links = page.get('links', [])
    if not isinstance(links, list) or any(not isinstance(x, Mapping) for x in links):
        reject()
    if 'totalItems' not in page and 'totalPages' not in page:
        if not records and not any(link.get('rel') == 'next' for link in links):
            return []
        reject()
    for field in ('totalItems', 'totalPages'):
        if (field not in page or not isinstance(page[field], int) or
                isinstance(page[field], bool) or page[field] < 0):
            reject()
    if page['totalItems'] > 0 and page['totalPages'] == 0:
        reject()
    if page.get('totalItems', len(records)) < len(records):
        reject()
    if complete and (page.get('totalPages', 1) > 1 or
                     page.get('totalItems', len(records)) != len(records) or
                     any(x.get('rel') == 'next' for x in links)):
        reject()
    ids = set()
    for record in records:
        if not isinstance(record, Mapping):
            reject()
        identifier = record.get('recordId')
        if (not isinstance(identifier, str) or not 0 < len(identifier) <= 2048 or
                identifier in ('.', '..') or
                any(ord(c) < 33 or ord(c) > 126 for c in identifier) or identifier in ids):
            reject()
        ids.add(identifier)
        if (not isinstance(record.get('name'), str) or
                not isinstance(record.get('type'), str) or
                not isinstance(record.get('data'), str) or
                not isinstance(record.get('ttl'), int) or isinstance(record['ttl'], bool) or
                record['ttl'] <= 0):
            reject()
        if name is not None and record['name'].lower().rstrip('.') != name.lower().rstrip('.'):
            reject()
        if record_type is not None and record['type'] != record_type:
            reject()
    return records


def godaddy_v3_accumulate(page, page_number, previous=None):
    """Require sequential, stable, duplicate-free pages and exact final totals."""
    def reject():
        raise AnsibleFilterError('Invalid or incomplete GoDaddy v3 DNS pagination')

    if (not isinstance(page_number, int) or isinstance(page_number, bool) or
            page_number < 1 or (previous is not None and not isinstance(previous, Mapping))):
        reject()
    previous = previous or {}
    records = godaddy_v3_records(page, complete=False)
    # v3 omits both totals for an empty result even with totalRequired=true.
    total, pages = page.get('totalItems', 0), page.get('totalPages', 0)
    if previous:
        if (page_number != previous['next_page'] or total != previous['totalItems'] or
                pages != previous['totalPages']):
            reject()
    elif page_number != 1:
        reject()
    if page_number > max(1, pages) or (total and not records):
        reject()
    combined = previous.get('records', []) + records
    if len({record['recordId'] for record in combined}) != len(combined):
        reject()
    complete = page_number == max(1, pages)
    if (len(combined) > total or (complete and len(combined) != total) or
            (not complete and len(combined) >= total) or
            (complete and any(link.get('rel') == 'next' for link in page.get('links', [])))):
        reject()
    return {'records': combined, 'totalItems': total, 'totalPages': pages,
            'next_page': page_number + 1, 'complete': complete}


def _dns_name(value):
    if not isinstance(value, str):
        raise AnsibleFilterError('Invalid DNS identity')
    name = value.lower().removesuffix('.')
    if (len(name) > 253 or '.' not in name or
            any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                for label in name.split('.'))):
        raise AnsibleFilterError('Invalid DNS identity')
    return name


def godaddy_v3_dns_response(result, question, record_type, authoritative=False, server=None):
    """Parse native dig output; a successful process alone is never DNS success."""
    def reject():
        raise AnsibleFilterError('DNS response does not prove the exact requested binding')

    if (not isinstance(result, Mapping) or result.get('rc') != 0 or
            isinstance(result.get('rc'), bool) or result.get('failed') is True or
            not isinstance(result.get('stdout'), str) or record_type not in ('A', 'NS')):
        reject()
    question = _dns_name(question)
    text = result['stdout']
    headers = re.findall(r'^;; ->>HEADER<<- opcode: (\w+), status: (\w+), id: \d+\s*$', text, re.M)
    flags = re.findall(r'^;; flags: ([a-z ]*); QUERY: (\d+), ANSWER: (\d+), AUTHORITY: \d+, ADDITIONAL: \d+\s*$', text, re.M)
    questions = re.findall(r'^;([^;\s]+)\s+IN\s+(\w+)\s*$', text, re.M)
    if (headers != [('QUERY', 'NOERROR')] or len(flags) != 1 or len(questions) != 1 or
            _dns_name(questions[0][0]) != question or questions[0][1] != record_type):
        reject()
    tokens, count, answer_count = flags[0]
    tokens = tokens.split()
    if ('qr' not in tokens or 'tc' in tokens or count != '1' or
            (authoritative and ('aa' not in tokens or 'rd' in tokens))):
        reject()
    if server is not None:
        servers = re.findall(r'^;; SERVER: ([0-9.]+)#53(?:\([^)]*\))?.*$', text, re.M)
        if servers != [str(IPv4Address(server))]:
            reject()
    section = False
    records = []
    for line in text.splitlines():
        line = line.strip()
        if line == ';; ANSWER SECTION:':
            if section or records:
                reject()
            section = True
            continue
        if line.startswith(';;'):
            section = False
        if not section or not line:
            continue
        match = re.fullmatch(r'(\S+)\s+(\d+)\s+IN\s+(\w+)\s+(\S+)', line)
        if not match or _dns_name(match[1]) != question or match[3] != record_type:
            reject()
        try:
            data = str(IPv4Address(match[4])) if record_type == 'A' else _dns_name(match[4])
        except ValueError:
            reject()
        records.append(data)
    if not records or int(answer_count) != len(records) or len(set(records)) != len(records):
        reject()
    return sorted(records)


def godaddy_v3_dns_nameservers(records, public_response, zone):
    """Bind provider-hosted apex NS records to public zone-apex discovery only."""
    if not isinstance(records, list) or not 1 <= len(records) <= 16:
        raise AnsibleFilterError('Require a bounded nonempty authoritative nameserver set')
    names = []
    for record in records:
        if (not isinstance(record, Mapping) or record.get('name') != '@' or
                record.get('type') != 'NS'):
            raise AnsibleFilterError('Require only provider apex NS records')
        names.append(_dns_name(record.get('data')))
    public = godaddy_v3_dns_response(public_response, zone, 'NS', server='8.8.8.8')
    if len(set(names)) != len(names) or sorted(names) != public:
        raise AnsibleFilterError('Provider and public zone-apex nameservers disagree')
    return public


def godaddy_v3_dns_endpoints(results, nameservers):
    """Resolve only the approved nameservers, retaining every returned IPv4."""
    if not isinstance(results, list) or len(results) != len(nameservers):
        raise AnsibleFilterError('Incomplete nameserver address observations')
    endpoints = []
    for result, name in zip(results, nameservers):
        if result.get('item') != name:
            raise AnsibleFilterError('Unexpected nameserver address observation')
        for address in godaddy_v3_dns_response(result, name, 'A', server='8.8.8.8'):
            endpoints.append({'nameserver': name, 'address': address})
    if not 1 <= len(endpoints) <= 32:
        raise AnsibleFilterError('Require a bounded nonempty nameserver IPv4 endpoint set')
    return endpoints


def godaddy_v3_dns_authority_round(results, endpoints, hostname, address):
    """Require all authorities in this round; retain negative rounds for retries."""
    if not isinstance(results, list) or len(results) != len(endpoints) or not endpoints:
        raise AnsibleFilterError('Incomplete authoritative DNS round')
    expected = str(IPv4Address(address))
    passed = []
    for result, endpoint in zip(results, endpoints):
        if result.get('item') != endpoint:
            raise AnsibleFilterError('Unexpected authoritative DNS endpoint observation')
        try:
            answers = godaddy_v3_dns_response(result, hostname, 'A', True, endpoint['address'])
            passed.append(answers == [expected])
        except (AnsibleFilterError, ValueError):
            passed.append(False)
    return {'ready': all(passed), 'authority_count': len(endpoints),
            'ready_count': sum(passed)}


class FilterModule:
    def filters(self):
        return {'godaddy_v3_records': godaddy_v3_records,
                'godaddy_v3_accumulate': godaddy_v3_accumulate,
                'godaddy_v3_dns_response': godaddy_v3_dns_response,
                'godaddy_v3_dns_nameservers': godaddy_v3_dns_nameservers,
                'godaddy_v3_dns_endpoints': godaddy_v3_dns_endpoints,
                'godaddy_v3_dns_authority_round': godaddy_v3_dns_authority_round}
