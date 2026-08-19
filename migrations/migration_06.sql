alter table public."마케팅활동" add column if not exists "정렬순서" integer;
with ranked as (
 select "활동ID", row_number() over (partition by "제품코드","활동분류","시작일" order by coalesce("시작일",date '9999-12-31'),"생성일시","활동ID")*10 rn
 from public."마케팅활동" where "계획실행구분"='계획'
)
update public."마케팅활동" a set "정렬순서"=r.rn from ranked r where a."활동ID"=r."활동ID" and a."정렬순서" is null;
alter table public."마케팅활동" alter column "정렬순서" set default 1000;
