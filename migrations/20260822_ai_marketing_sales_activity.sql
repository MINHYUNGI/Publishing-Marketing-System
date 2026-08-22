begin;

create table if not exists public."AI마케팅영업기록" (
  "기록ID" uuid primary key default gen_random_uuid(),
  "요청ID" uuid not null unique,
  "채널" text not null check (btrim("채널") <> ''),
  "담당자ID" uuid not null references public."사용자"("사용자ID") on update cascade on delete restrict,
  "담당자명" text not null,
  "등록자ID" uuid not null references public."사용자"("사용자ID") on update cascade on delete restrict,
  "거래처명" text,
  "제품코드" text references public."ERP제품마스터"("제품코드") on update cascade on delete restrict,
  "제품명" text,
  "ISBN" text,
  "활동유형" text,
  "활동시작일" date,
  "활동종료일" date,
  "성과발생일" date,
  "날짜표현원문" text,
  "미팅횟수" integer check ("미팅횟수" is null or "미팅횟수" >= 0),
  "제안서발송여부" boolean,
  "샘플제공여부" boolean,
  "납품부수" bigint check ("납품부수" is null or "납품부수" >= 0),
  "매출액" bigint check ("매출액" is null or "매출액" >= 0),
  "영업이익" bigint,
  "영업이익률" numeric(9,4),
  "활동요약" text,
  "상세내용" text,
  "기타성과" text,
  "비고" text,
  "원문" text not null check (btrim("원문") <> ''),
  "AI분석JSON" jsonb not null,
  "생성일시" timestamptz not null default now(),
  "수정일시" timestamptz not null default now(),
  check ("활동종료일" is null or "활동시작일" is null or "활동종료일" >= "활동시작일")
);

create table if not exists public."AI마케팅영업세부활동" (
  "세부활동ID" uuid primary key default gen_random_uuid(),
  "기록ID" uuid not null references public."AI마케팅영업기록"("기록ID") on update cascade on delete cascade,
  "활동유형" text not null check (btrim("활동유형") <> ''),
  "활동일" date,
  "시작일" date,
  "종료일" date,
  "날짜표현원문" text,
  "횟수" integer check ("횟수" is null or "횟수" >= 0),
  "내용" text,
  "정렬순서" integer not null default 10,
  "생성일시" timestamptz not null default now(),
  "수정일시" timestamptz not null default now(),
  check ("종료일" is null or "시작일" is null or "종료일" >= "시작일")
);

create index if not exists "AI마케팅영업기록_담당자ID_idx" on public."AI마케팅영업기록"("담당자ID");
create index if not exists "AI마케팅영업기록_등록자ID_idx" on public."AI마케팅영업기록"("등록자ID");
create index if not exists "AI마케팅영업기록_제품코드_idx" on public."AI마케팅영업기록"("제품코드") where "제품코드" is not null;
create index if not exists "AI마케팅영업기록_채널_idx" on public."AI마케팅영업기록"("채널");
create index if not exists "AI마케팅영업기록_성과발생일_idx" on public."AI마케팅영업기록"("성과발생일") where "성과발생일" is not null;
create index if not exists "AI마케팅영업세부활동_기록ID_idx" on public."AI마케팅영업세부활동"("기록ID");

alter table public."AI마케팅영업기록" enable row level security;
alter table public."AI마케팅영업세부활동" enable row level security;

create or replace function public."AI마케팅영업기록_수정일시_갱신"()
returns trigger
language plpgsql
set search_path = pg_catalog, public
as $$
begin
  new."수정일시" := now();
  return new;
end;
$$;

drop trigger if exists "AI마케팅영업기록_수정일시" on public."AI마케팅영업기록";
create trigger "AI마케팅영업기록_수정일시"
before update on public."AI마케팅영업기록"
for each row execute function public."AI마케팅영업기록_수정일시_갱신"();

drop trigger if exists "AI마케팅영업세부활동_수정일시" on public."AI마케팅영업세부활동";
create trigger "AI마케팅영업세부활동_수정일시"
before update on public."AI마케팅영업세부활동"
for each row execute function public."AI마케팅영업기록_수정일시_갱신"();

create or replace function public."AI마케팅영업기록_확정저장"(
  p_record jsonb,
  p_details jsonb default '[]'::jsonb
)
returns jsonb
language plpgsql
set search_path = pg_catalog, public
as $$
declare
  v_record_id uuid;
  v_request_id uuid;
  v_detail jsonb;
  v_detail_count integer := 0;
begin
  v_request_id := nullif(p_record->>'요청ID', '')::uuid;
  if v_request_id is null then
    raise exception '요청ID가 필요합니다.';
  end if;

  select "기록ID" into v_record_id
  from public."AI마케팅영업기록"
  where "요청ID" = v_request_id;
  if v_record_id is not null then
    return jsonb_build_object('기록ID', v_record_id, '중복', true, '세부활동수',
      (select count(*) from public."AI마케팅영업세부활동" where "기록ID" = v_record_id));
  end if;

  if not exists (
    select 1 from public."사용자"
    where "사용자ID" = nullif(p_record->>'담당자ID', '')::uuid and "사용여부" = true
  ) then raise exception '유효한 담당자를 찾을 수 없습니다.'; end if;
  if not exists (
    select 1 from public."사용자"
    where "사용자ID" = nullif(p_record->>'등록자ID', '')::uuid and "사용여부" = true
  ) then raise exception '유효한 등록자를 찾을 수 없습니다.'; end if;
  if nullif(p_record->>'제품코드', '') is not null and not exists (
    select 1 from public."ERP제품마스터" where "제품코드" = p_record->>'제품코드'
  ) then raise exception 'ERP제품마스터에 없는 제품코드입니다: %', p_record->>'제품코드'; end if;

  insert into public."AI마케팅영업기록" (
    "요청ID","채널","담당자ID","담당자명","등록자ID","거래처명","제품코드","제품명","ISBN",
    "활동유형","활동시작일","활동종료일","성과발생일","날짜표현원문","미팅횟수",
    "제안서발송여부","샘플제공여부","납품부수","매출액","영업이익","영업이익률",
    "활동요약","상세내용","기타성과","비고","원문","AI분석JSON"
  ) values (
    v_request_id,btrim(p_record->>'채널'),(p_record->>'담당자ID')::uuid,p_record->>'담당자명',(p_record->>'등록자ID')::uuid,
    nullif(p_record->>'거래처명',''),nullif(p_record->>'제품코드',''),nullif(p_record->>'제품명',''),nullif(p_record->>'ISBN',''),
    nullif(p_record->>'활동유형',''),nullif(p_record->>'활동시작일','')::date,nullif(p_record->>'활동종료일','')::date,
    nullif(p_record->>'성과발생일','')::date,nullif(p_record->>'날짜표현원문',''),nullif(p_record->>'미팅횟수','')::integer,
    nullif(p_record->>'제안서발송여부','')::boolean,nullif(p_record->>'샘플제공여부','')::boolean,
    nullif(p_record->>'납품부수','')::bigint,nullif(p_record->>'매출액','')::bigint,nullif(p_record->>'영업이익','')::bigint,
    nullif(p_record->>'영업이익률','')::numeric,nullif(p_record->>'활동요약',''),nullif(p_record->>'상세내용',''),
    nullif(p_record->>'기타성과',''),nullif(p_record->>'비고',''),p_record->>'원문',coalesce(p_record->'AI분석JSON','{}'::jsonb)
  ) returning "기록ID" into v_record_id;

  for v_detail in select value from jsonb_array_elements(coalesce(p_details,'[]'::jsonb)) loop
    insert into public."AI마케팅영업세부활동" (
      "기록ID","활동유형","활동일","시작일","종료일","날짜표현원문","횟수","내용","정렬순서"
    ) values (
      v_record_id,btrim(v_detail->>'활동유형'),nullif(v_detail->>'활동일','')::date,
      nullif(v_detail->>'시작일','')::date,nullif(v_detail->>'종료일','')::date,
      nullif(v_detail->>'날짜표현원문',''),nullif(v_detail->>'횟수','')::integer,
      nullif(v_detail->>'내용',''),coalesce(nullif(v_detail->>'정렬순서','')::integer,(v_detail_count+1)*10)
    );
    v_detail_count := v_detail_count + 1;
  end loop;
  return jsonb_build_object('기록ID',v_record_id,'중복',false,'세부활동수',v_detail_count);
end;
$$;

revoke all on table public."AI마케팅영업기록" from public, anon, authenticated;
revoke all on table public."AI마케팅영업세부활동" from public, anon, authenticated;
grant select,insert,update,delete on table public."AI마케팅영업기록" to service_role;
grant select,insert,update,delete on table public."AI마케팅영업세부활동" to service_role;
revoke execute on function public."AI마케팅영업기록_수정일시_갱신"() from public, anon, authenticated;
revoke execute on function public."AI마케팅영업기록_확정저장"(jsonb,jsonb) from public, anon, authenticated;
grant execute on function public."AI마케팅영업기록_확정저장"(jsonb,jsonb) to service_role;

commit;
