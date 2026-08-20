create table if not exists public."마케팅실행활동" (
  "실행활동ID" uuid primary key default gen_random_uuid(),
  "제품코드" text not null,
  "원본활동ID" uuid null references public."마케팅활동"("활동ID") on delete set null,
  "활동분류" text not null,
  "채널또는매체" text null,
  "활동명" text not null,
  "실제시작일" date null,
  "실제종료일" date null,
  "실제비용" bigint null,
  "실행구분" text not null default '실행확인'
    check ("실행구분" in ('실행확인','활동추가','활동취소')),
  "실행내용" text null,
  "등록자ID" uuid null references public."사용자"("사용자ID") on delete set null,
  "생성일시" timestamptz not null default now(),
  "수정일시" timestamptz not null default now(),
  constraint "마케팅실행활동_원본활동ID_unique" unique ("원본활동ID")
);

create index if not exists "idx_마케팅실행활동_제품코드"
  on public."마케팅실행활동"("제품코드");
create index if not exists "idx_마케팅실행활동_활동분류"
  on public."마케팅실행활동"("활동분류");
