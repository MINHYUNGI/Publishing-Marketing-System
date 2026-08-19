create extension if not exists pgcrypto;

alter table public."마케팅활동"
  add column if not exists "실행상태" text,
  add column if not exists "실제시작일" date,
  add column if not exists "실제종료일" date,
  add column if not exists "실제비용" bigint,
  add column if not exists "성과메모" text;

create table if not exists public."판매실적일별" (
  "판매실적ID" uuid primary key default gen_random_uuid(),
  "제품코드" text not null,
  "판매일" date not null,
  "SCM실판매부수" integer not null default 0,
  "SCM환산매출액" bigint not null default 0,
  "ERP출고부수" integer not null default 0,
  "ERP매출액" bigint not null default 0,
  "원천구분" text not null default '시스템',
  "원천파일명" text,
  "생성일시" timestamptz not null default now(),
  "수정일시" timestamptz not null default now(),
  constraint "판매실적일별_제품코드_판매일_key" unique ("제품코드","판매일")
);
create index if not exists "판매실적일별_제품일_idx" on public."판매실적일별" ("제품코드","판매일");

create table if not exists public."콘텐츠성과" (
  "콘텐츠성과ID" uuid primary key default gen_random_uuid(),
  "제품코드" text not null,
  "활동ID" uuid references public."마케팅활동"("활동ID") on delete set null,
  "플랫폼" text,
  "채널명" text,
  "콘텐츠명" text not null,
  "게시일" date,
  "URL" text,
  "조회수" bigint,
  "좋아요수" bigint,
  "댓글수" bigint,
  "공유수" bigint,
  "저장수" bigint,
  "클릭수" bigint,
  "지표수집일" date not null default current_date,
  "원천구분" text not null default '수동',
  "비고" text,
  "생성일시" timestamptz not null default now(),
  "수정일시" timestamptz not null default now()
);
create index if not exists "콘텐츠성과_제품게시일_idx" on public."콘텐츠성과" ("제품코드","게시일");

create table if not exists public."구매자반응" (
  "구매자반응ID" uuid primary key default gen_random_uuid(),
  "제품코드" text not null,
  "기준일" date not null default current_date,
  "데이터출처" text not null default 'YES24',
  "남성비율" numeric(6,3),
  "여성비율" numeric(6,3),
  "10대이하비율" numeric(6,3),
  "20대비율" numeric(6,3),
  "30대비율" numeric(6,3),
  "40대비율" numeric(6,3),
  "50대비율" numeric(6,3),
  "60대이상비율" numeric(6,3),
  "20대초비율" numeric(6,3),
  "20대후비율" numeric(6,3),
  "30대초비율" numeric(6,3),
  "30대후비율" numeric(6,3),
  "40대초비율" numeric(6,3),
  "40대후비율" numeric(6,3),
  "50대초비율" numeric(6,3),
  "50대후비율" numeric(6,3),
  "원천파일명" text,
  "생성일시" timestamptz not null default now(),
  "수정일시" timestamptz not null default now(),
  constraint "구매자반응_제품코드_기준일_출처_key" unique ("제품코드","기준일","데이터출처")
);
create index if not exists "구매자반응_제품기준일_idx" on public."구매자반응" ("제품코드","기준일" desc);

create table if not exists public."마케팅성과평가" (
  "성과평가ID" uuid primary key default gen_random_uuid(),
  "제품코드" text not null,
  "평가기준일" date not null default current_date,
  "PM자체평가" text,
  "성과코멘트" text,
  "잘된점" text,
  "개선보완필요" text,
  "다음액션플랜" text,
  "다음리뷰일" date,
  "등록자ID" uuid,
  "생성일시" timestamptz not null default now(),
  "수정일시" timestamptz not null default now(),
  constraint "마케팅성과평가_제품코드_평가기준일_key" unique ("제품코드","평가기준일")
);
create index if not exists "마케팅성과평가_제품기준일_idx" on public."마케팅성과평가" ("제품코드","평가기준일" desc);
