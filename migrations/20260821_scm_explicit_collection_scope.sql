-- 사용자가 선택한 날짜/거래처를 명시적인 교체 범위로 기록합니다.
-- 판매 0건인 날짜도 범위에 포함하여 마지막 수집 결과로 완전히 교체할 수 있습니다.
create table if not exists public."SCM동기화범위" (
  "동기화ID" uuid not null references public."SCM동기화이력" ("동기화ID") on delete cascade,
  "판매일" date not null,
  "거래처코드" text not null references public."SCM거래처" ("거래처코드") on update cascade on delete restrict,
  primary key ("동기화ID", "판매일", "거래처코드")
);

create index if not exists "SCM동기화범위_거래처_판매일_idx"
  on public."SCM동기화범위" ("거래처코드", "판매일");

alter table public."SCM동기화범위" enable row level security;
revoke all on table public."SCM동기화범위" from anon, authenticated;
grant select, insert, update, delete on table public."SCM동기화범위" to service_role;

-- 기존 행 기준 확정 함수는 실제 삽입/YES24 구매자 교체 로직으로 보존합니다.
alter function public."SCM동기화확정"(uuid) rename to "SCM동기화확정_행기준";
revoke all on function public."SCM동기화확정_행기준"(uuid) from public, anon, authenticated;
grant execute on function public."SCM동기화확정_행기준"(uuid) to service_role;

create function public."SCM동기화확정"("대상동기화ID" uuid)
returns table ("반영건수" bigint, "판매수량합계" bigint, "YES24스냅샷건수" bigint, "YES24분포건수" bigint)
language plpgsql
security invoker
set search_path = public
set statement_timeout = '300s'
as $$
declare
  scope_count bigint;
  staged_count bigint;
begin
  select count(*) into scope_count
  from public."SCM동기화범위" scope
  where scope."동기화ID" = "대상동기화ID";

  if scope_count = 0 then
    raise exception '확정할 SCM 동기화 범위가 없습니다.';
  end if;

  -- 선택한 날짜/거래처는 신규 파일에 행이 0건이어도 기존 값을 제거합니다.
  delete from public."SCM일별실판매" fact
  using public."SCM동기화범위" scope
  where scope."동기화ID" = "대상동기화ID"
    and fact."판매일" = scope."판매일"
    and fact."거래처코드" = scope."거래처코드";

  select count(*) into staged_count
  from public."SCM동기화스테이징" staged
  where staged."동기화ID" = "대상동기화ID";

  if staged_count = 0 then
    return query select 0::bigint, 0::bigint, 0::bigint, 0::bigint;
    return;
  end if;

  return query
  select * from public."SCM동기화확정_행기준"("대상동기화ID");
end;
$$;

revoke all on function public."SCM동기화확정"(uuid) from public, anon, authenticated;
grant execute on function public."SCM동기화확정"(uuid) to service_role;
