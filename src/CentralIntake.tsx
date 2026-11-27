import {useCallback, useEffect, useState, type FormEvent} from 'react';
import {FileText} from 'lucide-react';
import './central-intake.css';

type Entry = {
  id: string; kind: 'pdf' | 'text'; title: string; company_id: string; source_url: string | null;
  rights_basis: string; created_at: string; stored_at: string | null; body_text?: string; sha256: string;
  origin_format?: 'document' | 'link';
  notes?: {id: string; points: string; related_cases: {id: string; title: string}[]}[];
};
type Site = {url: string; title: string; category: string; note: string};
type IntakePage = {entries: Entry[]; sites: Site[]; has_more: boolean; can_write: boolean};
type Props = {csrf: string; onAuthRequired: () => void; onLogout: () => Promise<void>};

const companies = {all: '공통', ckd: '종근당', hold: '종근당홀딩스', kb: '경보제약'};
const categories = {filing: '공시', regulation: '법령·규정', guidance: '작성 지침', other: '기타'};
const errors: Record<string, string> = {
  invalid_intake_pdf: '열 수 있는 PDF(10MiB 이하)를 선택하세요.',
  invalid_intake_url: '사용자명과 비밀번호가 없는 HTTPS 주소를 입력하세요.',
  invalid_intake: '제목과 자료 형식에 필요한 항목을 확인하세요.',
  intake_editor_required: '현재 계정은 조회 권한입니다. 접수에는 작업공간 편집 권한이 필요합니다.',
  intake_pending_other_editor: '다른 편집자가 처리 중인 접수입니다. 잠시 뒤 목록을 다시 확인하세요.',
  intake_integrity_failed: '파일 식별값이 일치하지 않아 저장을 완료하지 못했습니다.',
  intake_missing: '해당 자료를 열 수 없습니다.',
};

function webLink(value: string | null) {
  if (!value) return undefined;
  try {
    const parsed = new URL(value);
    return parsed.protocol === 'https:' && !parsed.username && !parsed.password ? parsed.href : undefined;
  } catch {return undefined;}
}

export default function CentralIntake({csrf, onAuthRequired, onLogout}: Props) {
  const [kind, setKind] = useState<'pdf' | 'text' | 'link'>('pdf');
  const [tab, setTab] = useState<'materials' | 'sites'>('materials');
  const [page, setPage] = useState(1);
  const [data, setData] = useState<IntakePage | null>(null);
  const [detail, setDetail] = useState<Entry | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const request = useCallback(async <T,>(path: string, options?: RequestInit): Promise<T> => {
    const response = await fetch(path, options);
    const result = await response.json();
    if (response.status === 401) onAuthRequired();
    if (!response.ok) throw new Error(result.error || 'intake_request_failed');
    return result;
  }, [onAuthRequired]);

  const reload = useCallback(async (selectedPage: number, signal?: AbortSignal) => {
    const result = await request<IntakePage>('/api/intake?page=' + selectedPage, {signal});
    if (!signal?.aborted) setData(result);
  }, [request]);

  useEffect(() => {
    const abort = new AbortController();
    reload(page, abort.signal).catch(cause => {
      if (!abort.signal.aborted) setError(errors[cause.message] || '중앙 저장소 목록을 열 수 없습니다.');
    });
    return () => abort.abort();
  }, [page, reload]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    const fieldsObject = Object.fromEntries([...fields].filter(([, value]) => typeof value === 'string'));
    const pdf = tab === 'materials' && kind === 'pdf';
    const file = fields.get('file');
    setError('');
    setMessage('');
    if (pdf && (!(file instanceof File) || !file.size || file.size > 10 * 1024 * 1024)) {
      setError(errors.invalid_intake_pdf);
      return;
    }
    setPending(true);
    try {
      const result = await request<{id?: string; existing?: boolean}>(
        '/api/intake/' + (tab === 'sites' ? 'sites' : kind), {
          method: 'POST', headers: pdf ? {
            'Content-Type': 'application/pdf', 'X-KDP-CSRF': csrf,
            'X-KDP-Intake': encodeURIComponent(JSON.stringify(fieldsObject)),
          } : {'Content-Type': 'application/json', 'X-KDP-CSRF': csrf},
          body: pdf ? file as File : JSON.stringify(fieldsObject),
        },
      );
      form.reset();
      setMessage(result.existing ? '같은 주소가 중앙 DB에 이미 등록돼 있습니다.' : '중앙 저장을 완료했습니다.');
      setPage(1);
      await reload(1);
    } catch (cause) {
      const code = (cause as Error).message;
      setError(errors[code] || '요청을 완료하지 못했습니다. 같은 자료로 다시 시도할 수 있습니다.');
    } finally {setPending(false);}
  }

  async function open(entry: Entry) {
    setDetail(null);
    setError('');
    try {setDetail(await request<Entry>('/api/intake/' + entry.id));}
    catch (cause) {setError(errors[(cause as Error).message] || '중앙 자료를 열 수 없습니다.');}
  }

  return <main className="ev-app ci-app">
    <header className="ev-top">
      <div className="ev-brand"><FileText size={22} aria-hidden/><span>공시 검토실</span></div>
      <h1>중앙 자료 접수</h1>
      <a href="#" className="ci-nav-link">원문 검토</a>
      <button className="ev-session-button" onClick={() => void onLogout().catch(() => setError('로그아웃하지 못했습니다.'))}>로그아웃</button>
    </header>
    <nav className="ci-tabs" aria-label="중앙 자료 종류">
      <button aria-pressed={tab === 'materials'} disabled={pending} onClick={() => setTab('materials')}>규정 자료</button>
      <button aria-pressed={tab === 'sites'} disabled={pending} onClick={() => setTab('sites')}>참고 공시 사이트</button>
    </nav>
    {!data && !error && <p role="status">작업공간을 여는 중…</p>}
    {data && !data.can_write && <p className="ci-info">{errors.intake_editor_required}</p>}
    <div className="ci-grid">
      <section className="ci-list" aria-label={tab === 'sites' ? '등록 사이트' : '접수한 자료'}>
        <h2>{tab === 'sites' ? '등록 사이트' : '접수한 자료'}</h2>
        {tab === 'sites' ? <ul>{data?.sites.map(site => {
          const url = webLink(site.url);
          return <li key={site.url}>
            <small>{categories[site.category as keyof typeof categories]}</small>
            {url ? <a href={url} target="_blank" rel="noreferrer">{site.title}</a> : <b>{site.title}</b>}
            {site.note && <p>{site.note}</p>}
          </li>;
        })}</ul> : <ul>{data?.entries.map(item => <li key={item.id}>
          <small>{item.origin_format === 'link' ? '링크' : item.kind === 'pdf' ? 'PDF' : '텍스트'} · {companies[item.company_id as keyof typeof companies]}
            {item.kind === 'pdf' && !item.stored_at && ' · 업로드 대기'}</small>
          <button className="ci-entry" onClick={() => void open(item)}>{item.title}</button>
          <time dateTime={item.created_at}>{new Date(item.created_at).toLocaleDateString('ko-KR')}</time>
        </li>)}</ul>}
        {data && !(tab === 'sites' ? data.sites.length : data.entries.length) && <p>저장된 항목이 없습니다.</p>}
        {data && (page > 1 || data.has_more) && <div className="ci-pages">
          <button disabled={page === 1} onClick={() => setPage(page - 1)}>이전</button>
          <span>{page}쪽</span><button disabled={!data.has_more} onClick={() => setPage(page + 1)}>다음</button>
        </div>}
      </section>
      {data?.can_write && <section className="ci-form">
        <h2>{tab === 'sites' ? '사이트 등록' : '자료 등록'}</h2>
        <form key={tab} onSubmit={event => void save(event)}>
          <fieldset disabled={pending}>
            {tab === 'sites' ? <>
              <label>사이트 이름<input name="title" required maxLength={160}/></label>
              <label>주소<input name="url" type="url" required maxLength={1024} placeholder="https://"/></label>
              <label>유형<select name="category">{Object.entries(categories).map(([key, label]) =>
                <option key={key} value={key}>{label}</option>)}</select></label>
              <label>참고 범위<textarea name="note" rows={2} maxLength={500}/></label>
            </> : <>
              <label>자료 형식<select value={kind} onChange={event => setKind(event.target.value as typeof kind)}>
                <option value="pdf">PDF 파일</option><option value="text">텍스트</option><option value="link">공시·규정 링크</option>
              </select></label>
              <label>자료 제목<input name="title" required maxLength={180}/></label>
              <label>검토 대상<select name="company_id">{Object.entries(companies).map(([key, label]) =>
                <option key={key} value={key}>{label}</option>)}</select></label>
              <label>{kind === 'link' ? '출처 주소' : '출처 주소 (선택)'}<input name="source_url" type="url" required={kind === 'link'} maxLength={1024} placeholder="https://"/></label>
              {kind === 'pdf' && <label>PDF 원본 (10MiB 이하)<input name="file" type="file" required accept="application/pdf,.pdf"/></label>}
              {kind === 'text' && <label>원문 텍스트<textarea name="text" required rows={5} maxLength={100000}/></label>}
              {kind !== 'link' && <label>중앙 보관 근거<input name="rights_basis" required maxLength={500} placeholder="예: 자체 작성 자료, 사내 보관 승인"/></label>}
              <label>검토 포인트 (선택)<textarea name="review_points" rows={3} maxLength={2000} placeholder="대상 조항, 변경 내용, 확인할 공시"/></label>
            </>}
            <button type="submit" className="ev-session-button">{pending ? '저장 중…' : '중앙 저장'}</button>
          </fieldset>
        </form>
      </section>}
    </div>
    {message && <p className="ci-info" role="status">{message}</p>}
    {error && <p className="ev-notice" role="alert">{error}</p>}
    {detail && tab === 'materials' && <section className="ci-detail">
      <h2>{detail.title}</h2>
      {detail.origin_format !== 'link' && <p>보관 근거 · {detail.rights_basis}</p>}
      {webLink(detail.source_url) && <a href={webLink(detail.source_url)} target="_blank" rel="noreferrer">출처 열기</a>}
      {detail.kind === 'text' && detail.origin_format !== 'link' && <pre>{detail.body_text}</pre>}
      {detail.kind === 'pdf' && (detail.stored_at ? <a href={'/api/intake/' + detail.id + '/pdf'} download>PDF 원본 내려받기</a> :
        <p>업로드가 완료되지 않았습니다. 같은 제목·대상·출처로 동일한 파일을 다시 접수하세요.</p>)}
      {detail.notes?.map(note => <div className="ci-context" key={note.id}>
        {note.points && <><h3>검토 포인트</h3><p>{note.points}</p></>}
        {!!note.related_cases.length && <><h3>관련 사례 후보</h3>
          <ul>{note.related_cases.map(item => <li key={item.id}>
            <a href={'http://127.0.0.1:4175/Key-Disclosure-Points/#cases-' + item.id} target="_blank" rel="noreferrer">{item.title}</a>
          </li>)}</ul></>}
      </div>)}
      <details><summary>SHA-256</summary><code>{detail.sha256}</code></details>
    </section>}
  </main>;
}
