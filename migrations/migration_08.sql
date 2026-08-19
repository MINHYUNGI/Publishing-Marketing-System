-- 출판 마케팅 운영 시스템 v2.2
-- 마케팅 기획의 전략정보를 제품 단위로 저장하기 위한 테이블

CREATE TABLE IF NOT EXISTS public."마케팅기획" (
  "기획ID" uuid NOT NULL DEFAULT gen_random_uuid(),
  "제품코드" text NOT NULL,
  "타깃독자" text,
  "핵심키워드" text[] NOT NULL DEFAULT '{}'::text[],
  "마케팅문구" text,
  "마케팅전략" text,
  "USP" text,
  "원본문서ID" uuid,
  "등록자ID" uuid,
  "생성일시" timestamp with time zone NOT NULL DEFAULT now(),
  "수정일시" timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "마케팅기획_pkey" PRIMARY KEY ("기획ID"),
  CONSTRAINT "마케팅기획_제품코드_key" UNIQUE ("제품코드"),
  CONSTRAINT "마케팅기획_제품코드_fkey"
    FOREIGN KEY ("제품코드") REFERENCES public."마케팅대상제품"("제품코드"),
  CONSTRAINT "마케팅기획_원본문서ID_fkey"
    FOREIGN KEY ("원본문서ID") REFERENCES public."문서"("문서ID") ON DELETE SET NULL,
  CONSTRAINT "마케팅기획_등록자ID_fkey"
    FOREIGN KEY ("등록자ID") REFERENCES public."사용자"("사용자ID") ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS "마케팅기획_제품코드_idx"
ON public."마케팅기획" ("제품코드");
