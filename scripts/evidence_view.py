"""Build inert display data from versioned, verified case-pack originals."""
from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re

from case_pack import compact, require, verified_pages
from collector import decode


TAGS = frozenset('article section div p blockquote h1 h2 h3 h4 h5 h6 ul ol li '
                 'table caption thead tbody tfoot tr th td strong b em i small sup sub pre br'.split())
VOID = frozenset('area base br col embed hr img input link meta param source track wbr'.split())
SPANS = {'rowspan', 'colspan'}


@dataclass
class Text:
    text: str
    start: int
    end: int


@dataclass
class Element:
    tag: str
    number: int
    attributes: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    parent: Element | None = field(default=None, repr=False)

    @property
    def id(self):
        return f'{self.tag}-{self.number}'


class InertHTML(HTMLParser):
    """Track the collector's text offsets while keeping only harmless markup."""
    def __init__(self):
        super().__init__()
        self.root = Element('section', 0)
        self.current = self.root
        self.skip = 0
        self.position = 0
        self.serial = 0
        self.parts = []
        self.spots = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if self.skip or tag not in TAGS:
            return
        safe = {}
        for key, value in attrs:
            if tag in ('td', 'th') and key in SPANS and value and re.fullmatch(r'[0-9]{1,3}', value):
                number = int(value)
                if number <= 100 and (number > 0 or key == 'rowspan'):
                    safe[key] = number
        self.serial += 1
        element = Element(tag, self.serial, safe, parent=self.current)
        self.current.children.append(element)
        if tag not in VOID:
            self.current = element

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if not self.skip and tag in TAGS:
            node = self.current
            while node.parent and node.tag != tag:
                node = node.parent
            if node.parent:
                self.current = node.parent
        # collector.Plain includes one literal separator after each table cell.
        if tag in ('td', 'th'):
            self.add_text('|', render=False)

    def handle_data(self, data):
        if not self.skip:
            self.add_text(data)

    def add_text(self, data, render=True):
        normalized = compact(data)
        start = self.position
        self.parts.append(normalized)
        self.position += len(normalized)
        if render:
            item = Text(data, start, self.position)
            self.current.children.append(item)
            if normalized:
                self.spots.append((item, self.current))


def within(node, ancestor):
    while node is not None:
        if node is ancestor:
            return True
        node = node.parent
    return False


def nearest(node, tags):
    while node and node.tag not in tags:
        node = node.parent
    return node


def marked_text(text, start, end):
    """Map whitespace-normalized offsets to exact original display characters."""
    indexes = [match.start() for match in re.finditer(r'\S', text.text)]
    a = max(start, text.start) - text.start
    b = min(end, text.end) - text.start
    if a >= b:
        return [{'text': text.text}] if text.text else []
    left, right = indexes[a], indexes[b - 1] + 1
    segments = [{'text': text.text[:left]}, {'text': text.text[left:right], 'marked': True},
                {'text': text.text[right:]}]
    return [segment for segment in segments if segment['text']]


def serialize(node, start, end):
    if isinstance(node, Text):
        return marked_text(node, start, end)
    children = [part for child in node.children for part in serialize(child, start, end)]
    if node.tag in ('table', 'thead', 'tbody', 'tfoot', 'tr'):
        children = [child for child in children if 'tag' in child or child.get('text', '').strip()]
    if node.tag == 'table':
        grouped = []
        rows = []
        for child in children:
            if child.get('tag') == 'tr':
                rows.append(child)
            else:
                if rows:
                    grouped.append({'tag': 'tbody', 'children': rows})
                    rows = []
                grouped.append(child)
        if rows:
            grouped.append({'tag': 'tbody', 'children': rows})
        children = grouped
    return [{'tag': node.tag, 'id': node.id, 'children': children, **node.attributes}]


def html_view(raw, verified_text, start, end):
    parsed = InertHTML()
    parsed.feed(decode(raw))
    parsed.close()
    require(''.join(parsed.parts) == verified_text, 'html_offset_mapping_unavailable')
    spots = [(chunk, owner) for chunk, owner in parsed.spots if chunk.start < end and chunk.end > start]
    require(bool(spots), 'html_anchor_has_no_display_text')
    owner = spots[0][1]
    shared = owner
    while not all(within(parent, shared) for _, parent in spots):
        shared = shared.parent
    table = nearest(shared, {'table'})
    paragraph = nearest(shared, {'p', 'li', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'})
    cell = nearest(owner, {'td', 'th'})
    row = nearest(owner, {'tr'})
    context = table or (paragraph.parent if paragraph and paragraph.parent else shared)
    if not table and context.parent and len(context.children) < 3:
        context = context.parent
    if table:
        # Keep header/row order and spans intact for tables.
        nodes = serialize(context, start, end)
    else:
        # For long statutes, focus on three adjacent blocks on either side.
        indices = [i for i, child in enumerate(context.children) if
                   (isinstance(child, Text) and child.start < end and child.end > start)
                   or (isinstance(child, Element) and any(within(parent, child) for _, parent in spots))]
        children = context.children
        if indices:
            children = children[max(0, min(indices) - 3):max(indices) + 4]
        contextual = Element(context.tag, context.number, context.attributes, children)
        nodes = serialize(contextual, start, end)
    return {'kind': 'html', 'nodes': nodes, 'section_id': (paragraph or shared).id,
            'table_id': table.id if table else None,
            'row_id': row.id if row else None,
            'cell_id': cell.id if cell and all(within(parent, cell) for _, parent in spots) else None}


def pdf_view(raw, verified_text, page_index, start, end):
    import pymupdf

    with pymupdf.open(stream=raw, filetype='pdf') as document:
        page = document[page_index]
        data = page.get_text('rawdict', flags=pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
        lines = []
        for block in data['blocks']:
            for line in block.get('lines', ()):
                chars = [(character, char['bbox'])
                         for span in line['spans'] for char in span['chars']
                         for character in compact(char['c'])]
                if chars:
                    lines.append(chars)
        require(''.join(character for line in lines for character, _ in line) == verified_text,
                'pdf_coordinate_text_mismatch')
        position = 0
        boxes = []
        for line in lines:
            hits = [box for _, box in line[max(0, start - position):max(0, end - position)]]
            if hits:
                boxes.append([min(b[0] for b in hits), min(b[1] for b in hits),
                              max(b[2] for b in hits), max(b[3] for b in hits)])
            position += len(line)
            if position >= end:
                break
        require(bool(boxes), 'pdf_coordinate_unavailable')
        return {'kind': 'pdf', 'boxes': boxes, 'page_index': page_index, 'page_count': len(document),
                'page_label': page.get_label() or None, 'intrinsic_rotation': page.rotation,
                'width': page.cropbox.width, 'height': page.cropbox.height,
                'coordinate_system': 'cropbox-top-left-unrotated-points'}


def evidence_view(source, anchor, raw):
    pages = verified_pages(source, raw)
    if anchor['kind'] == 'visual':
        return {'kind': 'image', 'location_note': anchor['location'], 'status': 'visual_review_recorded'}
    start = anchor['start']
    end = start + len(compact(anchor['text']))
    if source['format'] == 'html':
        result = html_view(raw, pages[0], start, end)
    elif source['format'] == 'pdf':
        index = anchor['pdf_page'] - 1
        result = pdf_view(raw, pages[index], index, start, end)
    else:
        from ai_analyzer import hwp_text
        raw_text = hwp_text(raw)
        index = [match.start() for match in re.finditer(r'\S', raw_text)]
        left, right = max(0, start - 125), min(len(index), end + 125)
        offset = index[left]
        context = raw_text[offset:index[right - 1] + 1]
        result = {'kind': 'text', 'nodes': marked_text(Text(context, left, right), start, end)}
    return {**result, 'status': 'text_verified', 'normalized_start': start,
            'normalized_end': end, 'text': anchor['text']}
