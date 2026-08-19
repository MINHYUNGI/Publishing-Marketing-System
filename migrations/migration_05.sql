create table if not exists public."마케팅참조파일" (
  "파일ID" uuid primary key default gen_random_uuid(),
  "제품코드" text not null references public."마케팅대상제품"("제품코드") on delete cascade,
  "활동ID" uuid null references public."마케팅활동"("활동ID") on delete set null,
  "파일분류" text not null default '참조파일',
  "원본파일명" text not null,
  "저장파일명" text not null,
  "파일경로" text not null,
  "파일형식" text null,
  "파일크기" bigint null,
  "설명" text null,
  "등록자ID" uuid null references public."사용자"("사용자ID") on delete set null,
  "생성일시" timestamptz not null default now(),
  "수정일시" timestamptz not null default now()
);
