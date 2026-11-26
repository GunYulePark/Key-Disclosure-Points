import {createElement, useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode} from 'react';
import {createRoot} from 'react-dom/client';
import {ArrowDownToLine, ExternalLink, FileSearch, RotateCw, Search} from 'lucide-react';
import type {PDFDocumentProxy} from 'pdfjs-dist';
import './evidence-viewer.css';

type Anchor = {id: string; label: string; page?: number; kind: 'visual' | 'text'};
type Source = {id: string; version_id: string; title: string; version_label: string; format: string; anchors: Anchor[]};
type ViewerSession = {mode: 'cache'; signed_in: true} | {mode: 'supabase'; signed_in: boolean; csrf: string};
type InertNode = {text: string; marked?: boolean} |
  {tag: string; id?: string; children: InertNode[]; rowspan?: number; colspan?: number};
type Meta = {source_id: string; version_id: string; anchor_id: string; title: string; sha256: string;
  version_label: string; source_url: string; raw_url: string; bytes: number; format: string; text?: string};
type Evidence = Meta & (
  {kind: 'html' | 'text'; nodes: InertNode[]; section_id?: string; table_id?: string; row_id?: string; cell_id?: string} |
  {kind: 'pdf'; boxes: number[][]; page_index: number; page_count: number; page_label: string | null;
    intrinsic_rotation: number; width: number; height: number} |
  {kind: 'image'; location_note: string}
);

const allowed = new Set('article section div p blockquote h1 h2 h3 h4 h5 h6 ul ol li table caption thead tbody tfoot tr th td strong b em i small sup sub pre br'.split(' '));
const formatName: Record<string, string> = {pdf: 'PDF', html: 'HTML', hwp: 'HWP', jpg: '이미지'};
const message: Record<string, string> = {
  original_unavailable: '이 원본이 이 PC에 없습니다. 복원한 뒤 다시 열어주세요.',
  version_or_anchor_not_found: '이 문서 버전에 해당 근거가 없습니다.',
  original_or_anchor_verification_failed: '원본의 해시 또는 인용 위치가 일치하지 않습니다.',
  cloud_request_failed: 'Supabase에 연결하지 못했습니다. 잠시 뒤 다시 시도하세요.',
  workspace_access_denied: '이 계정에는 개발 작업공간 접근 권한이 없습니다.',
  auth_signin_failed: '개발 프로젝트 Auth 이메일과 비밀번호를 확인하세요.',
  invalid_login_form: '이메일과 비밀번호를 입력하세요.',
  local_origin_required: '브라우저에서 이 페이지를 다시 연 뒤 시도하세요.',
};

function readRoute() {
  const parts = window.location.hash.split('/');
  if (parts[0] !== '#viewer' || parts.length !== 3) return null;
  try {
    return {version: decodeURIComponent(parts[1]), anchor: decodeURIComponent(parts[2])};
  } catch {return null;}
}

function linkTo(version: string, anchor: string) {
  return '#viewer/' + encodeURIComponent(version) + '/' + encodeURIComponent(anchor);
}

async function json<T>(path: string, options: RequestInit): Promise<T> {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'request_failed');
  return body as T;
}

function inert(node: InertNode, key: number): ReactNode {
  if ('text' in node) return node.marked ? <mark key={key}>{node.text}</mark> : node.text;
  // Never insert source HTML. Construct only explicit inert elements and attributes.
  if (!allowed.has(node.tag)) return null;
  const props = {key, id: node.id, rowSpan: node.rowspan, colSpan: node.colspan};
  return node.tag === 'br'
    ? createElement('br', props)
    : createElement(node.tag, props, node.children.map(inert));
}

function centerInside(container: HTMLElement | null, child: Element | null) {
  if (!container || !child) return;
  const frame = container.getBoundingClientRect(), target = child.getBoundingClientRect();
  if (target.top < frame.top || target.bottom > frame.bottom) {
    container.scrollTop += target.top - frame.top - (container.clientHeight - target.height) / 2;
  }
  if (target.left < frame.left || target.right > frame.right) {
    container.scrollLeft += target.left - frame.left - (container.clientWidth - target.width) / 2;
  }
}

function HtmlDocument({data}: {data: Extract<Evidence, {nodes: InertNode[]}>}) {
  const documentBody = useRef<HTMLDivElement>(null);
  useEffect(() => {
    centerInside(documentBody.current, documentBody.current?.querySelector('mark') || null);
  }, [data]);
  return <div className={data.kind === 'text' ? 'ev-html ev-text' : 'ev-html'} ref={documentBody} tabIndex={0}
    aria-label="원문 및 강조 표시">
    {data.nodes.map(inert)}
  </div>;
}

function PdfDocument({data}: {data: Extract<Evidence, {kind: 'pdf'}>}) {
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null);
  const [pageIndex, setPage] = useState(data.page_index);
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  const [size, setSize] = useState({width: 0, height: 0});
  const [boxes, setBoxes] = useState<{x: number; y: number; width: number; height: number}[]>([]);
  const canvas = useRef<HTMLCanvasElement>(null);
  const scroll = useRef<HTMLDivElement>(null);
  const firstHighlight = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const abort = new AbortController();
    let dispose: (() => Promise<void>) | undefined;
    let cancelled = false;
    load().catch(() => {if (!cancelled) setError('PDF 파일을 열 수 없습니다.');});
    async function load() {
      const pdfjs = await import('pdfjs-dist');
      const response = await fetch(data.raw_url, {signal: abort.signal});
      if (!response.ok) throw new Error('original_unavailable');
      const bytes = await response.arrayBuffer();
      if (cancelled) return;
      pdfjs.GlobalWorkerOptions.workerSrc = '/vendor/pdf.worker.min.mjs';
      const task = pdfjs.getDocument({data: bytes, cMapUrl: '/vendor/cmaps/', cMapPacked: true,
        standardFontDataUrl: '/vendor/standard_fonts/', wasmUrl: '/vendor/wasm/'});
      dispose = () => task.destroy();
      const result = await task.promise;
      if (!cancelled) setDoc(result);
    }
    return () => {cancelled = true; abort.abort(); void dispose?.();};
  }, [data.raw_url]);

  useEffect(() => {
    if (!doc) return;
    let cancelled = false;
    let cancelRender: (() => void) | undefined;
    setReady(false);
    setError('');
    setBoxes([]);
    render().catch(() => {if (!cancelled) setError('PDF 페이지를 표시할 수 없습니다.');});
    async function render() {
      const target = canvas.current;
      if (!doc || !target) return;
      const page = await doc.getPage(pageIndex + 1);
      if (cancelled) return;
      const viewport = page.getViewport({scale: zoom, rotation: (page.rotate + rotation) % 360});
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      target.width = Math.ceil(viewport.width * ratio);
      target.height = Math.ceil(viewport.height * ratio);
      setSize({width: viewport.width, height: viewport.height});
      const task = page.render({canvas: target, viewport,
        transform: ratio === 1 ? undefined : [ratio, 0, 0, ratio, 0, 0]});
      cancelRender = () => task.cancel();
      await task.promise;
      if (cancelled) return;
      if (pageIndex === data.page_index) {
        const [left, bottom, right, top] = page.view;
        if (Math.abs((right - left) - data.width) > .5 || Math.abs((top - bottom) - data.height) > .5) {
          setError('PDF 좌표계가 원본과 일치하지 않아 강조 표시를 숨겼습니다.');
        } else {
          const [a, b, c, d, e, f] = viewport.transform;
          const point = (x: number, y: number) => {
            const px = left + x, py = top - y;
            return [a * px + c * py + e, b * px + d * py + f];
          };
          setBoxes(data.boxes.map(([x1, y1, x2, y2]) => {
            const p = point(x1, y1), q = point(x2, y2);
            return {x: Math.min(p[0], q[0]), y: Math.min(p[1], q[1]),
              width: Math.abs(p[0] - q[0]), height: Math.abs(p[1] - q[1])};
          }));
        }
      }
      setReady(true);
    }
    return () => {cancelled = true; cancelRender?.();};
  }, [doc, pageIndex, zoom, rotation, data]);

  useEffect(() => {centerInside(scroll.current, firstHighlight.current);}, [boxes]);
  return <div className="ev-pdf">
    <div className="ev-pdf-tools" aria-label="PDF 도구">
      <button disabled={pageIndex === 0} onClick={() => setPage(pageIndex - 1)}>이전</button>
      <span>{pageIndex + 1} / {data.page_count}쪽</span>
      <button disabled={pageIndex + 1 >= data.page_count} onClick={() => setPage(pageIndex + 1)}>다음</button>
      <button disabled={pageIndex === data.page_index} onClick={() => setPage(data.page_index)}>인용 쪽</button>
      <label>배율 <select value={zoom} onChange={e => setZoom(Number(e.target.value))}>
        <option value={.75}>75%</option><option value={1}>100%</option><option value={1.25}>125%</option>
        <option value={1.5}>150%</option><option value={2}>200%</option>
      </select></label>
      <button onClick={() => setRotation((rotation + 90) % 360)} aria-label="오른쪽으로 90도 회전">
        <RotateCw size={15} aria-hidden/> 회전
      </button>
    </div>
    {error && <p className="ev-notice" role="alert">{error}</p>}
    {(!ready && !error) && <p className="ev-notice" role="status">PDF 페이지 여는 중…</p>}
    <div className="ev-pdf-scroll" ref={scroll} tabIndex={0} aria-label="PDF 원본 페이지">
      <div className="ev-paper" style={size} aria-hidden={!ready}>
        <canvas ref={canvas} style={size} aria-label={`PDF ${pageIndex + 1}쪽`}/>
        {boxes.map((b, i) => <span ref={i === 0 ? firstHighlight : undefined} className="ev-pdf-box" key={i}
          style={{left: b.x, top: b.y, width: b.width, height: b.height}} aria-hidden/>)}
      </div>
    </div>
  </div>;
}

function EvidenceApp({cloud, onAuthRequired, onLogout}: {
  cloud: boolean; onAuthRequired: () => void; onLogout: () => Promise<void>;
}) {
  const [sources, setSources] = useState<Source[]>([]);
  const [route, setRoute] = useState(readRoute);
  const [data, setData] = useState<Evidence | null>(null);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [catalogError, setCatalogError] = useState(false);
  const [catalogReady, setCatalogReady] = useState(false);
  const [logoutPending, setLogoutPending] = useState(false);
  const [logoutError, setLogoutError] = useState(false);
  const navigation = useRef<HTMLElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    const onHash = () => setRoute(readRoute());
    window.addEventListener('hashchange', onHash);
    json<{sources: Source[]}>('/api/catalog', {signal: controller.signal}).then(result => {
      setSources(result.sources);
      setCatalogReady(true);
      const initial = result.sources.find(s => s.id === 'commercial-decree-33') || result.sources[0];
      if (initial && !window.location.hash) {
        const anchor = initial.anchors.find(item => item.id === 'commercial-decree-33:2') || initial.anchors[0];
        history.replaceState(null, '', linkTo(initial.version_id, anchor.id));
        onHash();
      }
    }).catch((error: Error) => {
      if (controller.signal.aborted) return;
      if (cloud && error.message === 'auth_required') onAuthRequired();
      else setCatalogError(true);
    });
    return () => {controller.abort(); window.removeEventListener('hashchange', onHash);};
  }, [cloud, onAuthRequired]);

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError('');
    if (route) {
      json<Evidence>('/api/evidence/' + encodeURIComponent(route.version) + '/' + encodeURIComponent(route.anchor),
        {signal: controller.signal}).then(setData).catch((error: Error) => {
          if (controller.signal.aborted) return;
          if (cloud && error.message === 'auth_required') onAuthRequired();
          else if (cloud && error.message === 'original_unavailable') setError('이 원본은 비공개 저장소에서 열 수 없습니다.');
          else setError(message[error.message] || '원문을 여는 중 오류가 발생했습니다.');
        });
    }
    return () => controller.abort();
  }, [route, cloud, onAuthRequired]);

  const selected = sources.find(s => s.version_id === route?.version);
  useEffect(() => {
    centerInside(navigation.current,
      navigation.current?.querySelector('[aria-current=location]') || null);
  }, [sources, route, query]);
  const filtered = sources.filter(s => `${s.title} ${s.version_label} ${s.id}`.toLowerCase().includes(query.trim().toLowerCase()));
  async function signOut() {
    setLogoutPending(true);
    setLogoutError(false);
    try {await onLogout();}
    catch {setLogoutError(true);}
    finally {setLogoutPending(false);}
  }
  return <main className="ev-app">
    <header className="ev-top"><div className="ev-brand"><FileSearch size={23} aria-hidden/><span>공시 검토실</span></div>
      <h1>원문 검토</h1><span className="ev-mode">{cloud ? 'Supabase 원본' : '개발 미리보기'}</span>
      {cloud && <button className="ev-session-button" disabled={logoutPending} onClick={() => void signOut()}>로그아웃</button>}
    </header>
    {logoutError && <p className="ev-notice" role="alert">로그아웃하지 못했습니다. 다시 시도하세요.</p>}
    <div className="ev-layout">
      <aside className="ev-sidebar" aria-label="문서와 근거">
        <div className="ev-side-head"><h2>문서</h2><span>{sources.length}개</span></div>
        <label className="ev-search"><Search size={17} aria-hidden/>
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="문서 제목 검색" aria-label="문서 제목 검색"/>
        </label>
        {catalogError && <p role="alert">문서 목록을 열 수 없습니다.</p>}
        <nav className="ev-sources" ref={navigation} aria-label="문서 목록">
          {filtered.map(source => <div key={source.version_id}>
            <a className="ev-source" data-active={source === selected}
              href={linkTo(source.version_id, source.anchors[0].id)} aria-current={source === selected ? 'true' : undefined}>
              <span className="ev-format">{formatName[source.format]}</span>
              <span><b>{source.title}</b><small>{source.version_label}</small></span>
            </a>
            {source === selected && <ul className="ev-anchors">{source.anchors.map(anchor =>
              <li key={anchor.id}><a href={linkTo(source.version_id, anchor.id)}
                aria-current={route?.anchor === anchor.id ? 'location' : undefined}>
                {anchor.page && <span>{anchor.page}쪽</span>}{anchor.label}
              </a></li>)}</ul>}
          </div>)}
          {!filtered.length && !catalogError && <p>{
            !catalogReady ? '목록을 읽는 중…' : sources.length ? '검색 결과가 없습니다.' : '열 수 있는 원본이 없습니다.'
          }</p>}
        </nav>
      </aside>
      <section className="ev-document" aria-label="선택한 원문">
        <div className="ev-document-head">
          <div className="ev-title"><p>{selected?.version_label || '문서와 버전을 선택하세요'}</p>
            <h2>{selected?.title || (route ? '원문 찾는 중' : '문서 선택')}</h2></div>
          {data && <div className="ev-links"><a href={data.source_url} target="_blank" rel="noreferrer">
            <ExternalLink size={16} aria-hidden/> 공식 출처</a>
            <a href={data.raw_url} download><ArrowDownToLine size={16} aria-hidden/> 원본 저장</a></div>}
        </div>
        {data && <div className="ev-citation">
          <p><strong>{data.kind === 'image' ? '수동 확인 위치' : '선택한 인용'}</strong>
            {data.kind === 'pdf' && <span>PDF {data.page_index + 1}쪽{data.page_label && ` · 인쇄 쪽 ${data.page_label}`}</span>}
            {data.kind === 'html' && data.table_id && <span>{data.cell_id ? '표 셀' : '표'}</span>}
            <span className="ev-verified">원본 SHA-256 일치</span></p>
          <blockquote>{data.kind === 'image' ? data.location_note : data.text}</blockquote>
        </div>}
        {error && <p className="ev-notice" role="alert">{error}</p>}
        {!error && !data && <p className="ev-notice" role="status">
          {route ? '원본과 근거 위치 확인 중…' : '문서 목록에서 근거를 선택하세요.'}</p>}
        {data && (data.kind === 'pdf' ? <PdfDocument key={data.anchor_id} data={data}/>
          : data.kind === 'image' ? <img className="ev-image" src={data.raw_url} alt={data.location_note}/>
          : <HtmlDocument data={data}/>)}
        {data && <details className="ev-meta"><summary>원본 버전과 식별값</summary><dl>
          <dt>문서 버전</dt><dd>{data.version_label}</dd><dt>버전 ID</dt><dd>{data.version_id}</dd>
          <dt>근거 ID</dt><dd>{data.anchor_id}</dd><dt>SHA-256</dt><dd>{data.sha256}</dd>
          <dt>파일 크기</dt><dd>{data.bytes.toLocaleString('ko-KR')} bytes</dd>
        </dl></details>}
      </section>
    </div>
  </main>;
}

function SignIn({csrf, completed}: {csrf: string; completed: (value: ViewerSession) => void}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    setPending(true);
    setError('');
    try {
      const session = await json<ViewerSession>('/api/session', {
        method: 'POST', headers: {'Content-Type': 'application/json', 'X-KDP-CSRF': csrf},
        body: JSON.stringify({email: fields.get('email'), password: fields.get('password')}),
      });
      form.reset();
      completed(session);
    } catch (cause) {
      const password = form.elements.namedItem('password');
      if (password instanceof HTMLInputElement) password.value = '';
      setError(message[(cause as Error).message] || '로그인하지 못했습니다.');
    } finally {setPending(false);}
  }
  return <main className="ev-app">
    <header className="ev-top"><div className="ev-brand"><FileSearch size={23} aria-hidden/><span>공시 검토실</span></div>
      <h1>원문 검토</h1><span className="ev-mode">Supabase 원본</span></header>
    <section className="ev-signin" aria-labelledby="ev-signin-title">
      <h2 id="ev-signin-title">프로젝트 Auth 로그인</h2>
      <p>개발 프로젝트에 등록한 계정으로 비공개 원본을 엽니다.</p>
      <form onSubmit={e => void submit(e)}>
        <label>이메일<input name="email" type="email" required autoComplete="username"/></label>
        <label>비밀번호<input name="password" type="password" required autoComplete="current-password"/></label>
        <button className="ev-session-button" type="submit" disabled={pending}>{pending ? '확인 중…' : '로그인'}</button>
      </form>
      {error && <p className="ev-signin-error" role="alert">{error}</p>}
    </section>
  </main>;
}

function ViewerRoot() {
  const [session, setSession] = useState<ViewerSession | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    json<ViewerSession>('/api/session', {signal: controller.signal}).then(setSession)
      .catch(() => {if (!controller.signal.aborted) setUnavailable(true);});
    return () => controller.abort();
  }, []);
  const requireLogin = useCallback(() => {
    setSession(current => current?.mode === 'supabase' ? {...current, signed_in: false} : current);
  }, []);
  async function logout() {
    if (session?.mode === 'supabase') {
      setSession(await json<ViewerSession>('/api/session/logout', {
        method: 'POST', headers: {'X-KDP-CSRF': session.csrf},
      }));
    }
  }
  if (!session) return <p className="ev-notice" role={unavailable ? 'alert' : 'status'}>
    {unavailable ? '원문 검토 서버에 연결하지 못했습니다.' : '원문 검토 여는 중…'}</p>;
  if (session.mode === 'supabase' && !session.signed_in) {
    return <SignIn csrf={session.csrf} completed={setSession}/>;
  }
  return <EvidenceApp cloud={session.mode === 'supabase'} onAuthRequired={requireLogin} onLogout={logout}/>;
}

createRoot(document.getElementById('evidence-root')!).render(<ViewerRoot/>);
