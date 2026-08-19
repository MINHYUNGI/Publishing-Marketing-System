-- v2.6.0 영업목표 / 사업계획 연동용 스키마 메모
-- 운영 DB에는 2026-08-19 기준 이미 반영되어 있으며, 신규 환경 재구성 시 사용합니다.

create table if not exists public."영업목표" (
  "영업목표ID" uuid primary key default gen_random_uuid(),
  "제품코드" text not null unique,
  "초도배본부수" integer,
  "초도배본매출액" bigint,
  "출간3개월부수" integer,
  "출간3개월매출액" bigint,
  "출간6개월부수" integer,
  "출간6개월매출액" bigint,
  "출간12개월부수" integer,
  "출간12개월매출액" bigint,
  "BEP부수" integer,
  "BEP매출액" bigint,
  "BEP초과목표개월" integer,
  "BEP초과목표메모" text,
  "원본문서ID" uuid,
  "등록자ID" uuid,
  "생성일시" timestamptz default now(),
  "수정일시" timestamptz default now()
);

create table if not exists public."사업계획목표" (
  "사업계획목표ID" uuid primary key default gen_random_uuid(),
  "사업계획연도" integer not null,
  "제품코드" text not null,
  "제품명" text,
  "계획정가" integer,
  "계획첫출고일" date,
  "연간계획부수" integer,
  "연간계획매출액" bigint,
  "원천파일명" text,
  "생성일시" timestamptz default now(),
  "수정일시" timestamptz default now(),
  unique("사업계획연도","제품코드")
);

create table if not exists public."사업계획월별목표" (
  "월별목표ID" uuid primary key default gen_random_uuid(),
  "사업계획연도" integer not null,
  "제품코드" text not null,
  "매출월" date not null,
  "계획부수" integer,
  "계획매출액" bigint,
  "계획정가" integer,
  "계획첫출고일" date,
  "원천파일명" text,
  "생성일시" timestamptz default now(),
  "수정일시" timestamptz default now(),
  unique("사업계획연도","제품코드","매출월")
);
