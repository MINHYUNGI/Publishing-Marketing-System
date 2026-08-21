-- Conservative security and FK-index cleanup. No business object is removed.
begin;

alter table public."판매실적일별" enable row level security;
alter table public."구매자반응" enable row level security;
alter table public."마케팅성과평가" enable row level security;
alter table public."ERP일별판매실적" enable row level security;
alter table public."콘텐츠성과" enable row level security;
alter table public."마케팅실행활동" enable row level security;

alter function public."마케팅활동_수정일시_갱신"() set search_path = pg_catalog, public;
alter function public."문서_수정일시_갱신"() set search_path = pg_catalog, public;
alter function public."마케팅활동이미지_수정일시_갱신"() set search_path = pg_catalog, public;
revoke execute on function public."마케팅활동_수정일시_갱신"() from public, anon, authenticated;
revoke execute on function public."문서_수정일시_갱신"() from public, anon, authenticated;
revoke execute on function public."마케팅활동이미지_수정일시_갱신"() from public, anon, authenticated;

-- Retain legacy RPCs for compatibility, but do not expose SECURITY DEFINER
-- execution to anonymous or ordinary authenticated Data API callers.
revoke execute on function public."마케팅기획목록조회"() from public, anon, authenticated;
revoke execute on function public."마케팅기획상세조회"(text) from public, anon, authenticated;
revoke execute on function public."마케팅대상제품기본정보저장"(text,text,date,text,text) from public, anon, authenticated;
grant execute on function public."마케팅기획목록조회"() to service_role;
grant execute on function public."마케팅기획상세조회"(text) to service_role;
grant execute on function public."마케팅대상제품기본정보저장"(text,text,date,text,text) to service_role;

create index if not exists "마케팅기획_등록자ID_idx" on public."마케팅기획"("등록자ID");
create index if not exists "마케팅기획_원본문서ID_idx" on public."마케팅기획"("원본문서ID");
create index if not exists "마케팅실행활동_등록자ID_idx" on public."마케팅실행활동"("등록자ID");
create index if not exists "마케팅참조파일_등록자ID_idx" on public."마케팅참조파일"("등록자ID");
create index if not exists "마케팅활동_등록자ID_idx" on public."마케팅활동"("등록자ID");
create index if not exists "영업목표_등록자ID_idx" on public."영업목표"("등록자ID");
create index if not exists "콘텐츠성과_활동ID_idx" on public."콘텐츠성과"("활동ID");

commit;
