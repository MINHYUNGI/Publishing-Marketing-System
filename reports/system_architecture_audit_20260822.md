# 출판 마케팅 운영 시스템 전체 구조 감사

- 기준일: 2026-08-22
- 대상: `Publishing-Marketing-System` main + Supabase `ttqeovahaitfkalbfucl`
- 원칙: UI/UX·운영 데이터 보존, 파괴적 DB 변경 금지
- 검증: Python 회귀 테스트 30개, 실제 service-role 연결 smoke test, Supabase advisor

## A. 시스템 구조

```text
ui/index.html, ui/scm-dashboard.html
  ↓ pywebview JS API
app/backend.py
  ↓ 유사 사용 사례 검증·오류 변환
app/database.py / erp_import.py / scm_collection.py / scm_import.py
  ↓
Supabase Data API(secret/service key) + Y: 문서·엑셀·첨부파일
```

- 제품 기준정보: `제품인덱스.제품코드`
- 마케팅 관리 루트: `마케팅대상제품.제품코드` → `마케팅기획` / `마케팅활동` / `마케팅실행활동`
- ERP: `ERP일별판매실적.제품코드`
- SCM: ISBN13 → `SCM제품매핑` → `제품인덱스.제품코드`
- YES24: `YES24구매자스냅샷` → `YES24구매자분포`, 제품코드·ISBN13 모두 보존
- 첨부: DB에 메타데이터, Y: 또는 운영 폴더에 실파일
- secret: Supabase/OpenAI/YouTube/SCM 자격 증명은 Windows Credential Manager

## B. 발견된 문제

### Critical — 조치 완료

1. `public` 6개 테이블의 RLS가 비활성이었다. 익명·일반 인증 요청을 차단하고 service-role 운영은 보존했다.
2. `SECURITY DEFINER` 과거 RPC 2개가 anon으로 호출 가능했다. 코드에서 사용하지 않음을 확인하고 service-role을 제외한 실행 권한을 회수했다.

### High

1. **조치 완료:** `run.ps1`, `restart_latest.ps1`의 `git reset --hard` 는 미커밋 작업을 삭제할 수 있었다. dirty worktree 보호 + `merge --ff-only`로 교체했다.
2. **추가 작업 후보:** `update_existing_plan`, `save_execution_group`, `delete_marketing_plan` 은 여러 Data API 요청으로 하나의 업무 작업을 처리한다. 중간 실패 시 부분 저장 가능성이 있어 후속 transaction RPC가 필요하다. 현재 화면 우선순위와 삭제 규칙을 보존해야 하므로 이번 차수에서 급히 전환하지 않았다.
3. **추가 작업 후보:** 로컬 migration 9개와 원격 migration 22개의 이력이 완전히 대칭하지 않는다. DB는 정상이지만 초기 migration 파일 복원/베이스라인 정리가 필요하다.

### Medium

1. `ui/index.html` 3,000줄+, `database.py` 1,200줄+, `backend.py` 800줄+로 책임이 넓다. UI/DB 공개 contract를 먼저 test로 고정한 후 Product/Marketing/Performance/Attachment repository 단위로 점진 분리해야 한다.
2. `판매실적일별`, `구매자반응`은 현재 실제 조회 결과를 ERP/SCM/YES24 세부 테이블에서 조립하므로 비어 있다. 즉시 삭제할 dead table이 아니며, 상위 API contract을 정리한 후 폐기 여부를 결정해야 한다.
3. 가입자/일반 사용자용 RLS policy가 없다. 현재는 service-key 전용 데스크톱 모델이라 의도된 차단 상태이지만, 향후 Supabase Auth를 도입하면 역할·소유권 policy가 먼저 필요하다.

### Low

1. 확정적 unused import 2개를 제거했다.
2. `legacy_v72.py`의 단독 참조 함수들은 Selenium 동적 호출·원본 대시보드 보존 가능성 때문에 dead code로 단정하지 않았다.
3. 사용 통계가 짧은 인덱스는 `unused_index` 정보가 있지만 삭제하지 않았다.

## C. 코드 정리 결과

- 제거: `app/file_store.py` unused `base64`, `legacy_v72.py` unused `sys`
- 보존: SCM 원본 UI/수집 코드, 현재 pywebview API 메서드, 비어 있는 호환성 테이블
- 분리 후보: `Database` → Product/Marketing/Performance/Attachment/SCM repository
- 분리 후보: `ui/index.html` → 화면별 JS/CSS module. 먼저 DOM contract/snapshot test 필요
- 안전성: Git 업데이트를 비파괴적 fast-forward로 변경

## D. 데이터베이스 분석

| 테이블 | 역할 | PK | 주요 연결 | 현재 판단 |
|---|---|---|---|---|
| 제품인덱스 | ERP 제품 기준정보 | 제품코드 | 마케팅대상/SCM/YES24 | 표준 제품 식별자, 보존 |
| 마케팅대상제품 | 마케팅 관리 대상 | 제품코드 | 제품인덱스, 사용자 | 보존 |
| 마케팅기획 | 제품별 전략 | 기획ID | 제품코드, 문서, 사용자 | 보존 |
| 마케팅활동 | 계획 활동 | 활동ID | 제품, 문서, 사용자 | 보존 |
| 마케팅실행활동 | 실제 실행 기록 | 실행활동ID | 제품, 원본활동, 사용자 | RLS/FK index 보강 |
| 콘텐츠성과 | SNS/바이럴 지표 | 콘텐츠성과ID | 제품, 활동, 실행활동 | RLS/FK index 보강 |
| 마케팅성과평가 | PM 정성 평가 | 성과평가ID | 제품코드 | RLS 보강, FK 후보 |
| 문서 | 원문서/AI 결과 | 문서ID | 제품, 사용자 | 보존 |
| 마케팅참조파일 | 첨부 메타데이터 | 파일ID | 제품, 활동, 사용자 | FK index 보강 |
| 마케팅활동이미지 | 구형 활동 이미지 | 이미지ID | 활동, 사용자 | 호환성 보존 |
| 영업목표 | 기획서 기준 목표 | 영업목표ID | 제품, 문서, 사용자 | FK index 보강 |
| 사업계획목표 | 연간 목표 | 사업계획목표ID | 제품코드 | FK 후보, 보존 |
| 사업계획월별목표 | 월별 목표 | 월별목표ID | 제품코드 | FK 후보, 보존 |
| ERP일별판매실적 | ERP 일별 실적 | ERP일별실적ID | 제품코드 | RLS 보강, FK 후보 |
| 판매실적일별 | 구형 통합 성과 그레인 | 판매실적ID | 제품코드 | 비어 있음, 바로 삭제 금지 |
| 구매자반응 | 구형 요약 반응 | 구매자반응ID | 제품코드 | 비어 있음, YES24 세부와 용도 중첩 |
| SCM거래처 | SCM 거래처 코드 | 거래처코드 | SCM 판매/동기화 | 보존 |
| SCM제품매핑 | ISBN crosswalk | ISBN13 | 제품인덱스 | 보존 |
| SCM일별실판매 | 일·거래처·ISBN 실판매 | SCM실판매ID | 거래처, 제품, 동기화 | 182,694건, 보존 |
| SCM동기화이력 | 수집/저장 런 | 동기화ID | 범위, 결과, staging | 보존 |
| SCM동기화범위 | 재수집 교체 범위 | 동기화ID+판매일+거래처 | 동기화, 거래처 | 보존 |
| SCM동기화결과 | 거래처별 결과 | 결과ID | 동기화, 거래처 | 보존 |
| SCM동기화스테이징 | 확정 전 원자 데이터 | 동기화+일+거래처+ISBN | 동기화 | 183,972건, 보존 |
| YES24구매자스냅샷 | 기준일·계정·ISBN 스냅샷 | 스냅샷ID | 제품, 동기화 | 11,195건, 보존 |
| YES24구매자분포 | 성별·연령·지역 원본 그레인 | 스냅샷+유형+구간 | 스냅샷 | 235,095건, 보존 |
| YES24구매자스테이징 | 확정 전 JSON 분포 | 동기화+기준일+계정+ISBN | 동기화 | 11,643건, 보존 |
| 사용자 | PM/등록자 | 사용자ID | 다수 등록자 FK | 보존 |

## E. DB 정리 식별

- 삭제 확정 table/column: 없음
- 정리 후보 table: `판매실적일별`, `구매자반응` (사용 contract 전환 후만)
- 추가 FK 후보: ERP일별판매실적/사업계획/성과평가/콘텐츠성과의 제품코드 → 제품인덱스 또는 마케팅대상제품. 고아 데이터 사전 검사 필요
- 추가 index: FK 누락 7개 반영
- index 삭제: 없음. 운영 사용 통계 누적 후 재평가
- 이름 차이: DB는 한글 `snake`를 사용하지 않고 UI payload는 영문 snake_case와 한글을 혼용. 현재 mapping이 검증되어 대규모 rename 금지

## F. 데이터 관계

```text
제품인덱스.제품코드
├─ 마케팅대상제품
│  ├─ 마케팅기획
│  ├─ 마케팅활동 → 마케팅실행활동 → 콘텐츠성과
│  └─ 문서 / 참조파일 / 영업목표
├─ ERP일별판매실적
└─ SCM제품매핑.ISBN13
   ├─ SCM일별실판매
   └─ YES24구매자스냅샷 → YES24구매자분포
```

시스템 표준 식별자는 `제품코드`이다. ISBN13은 외부 SCM 원천을 보존하고 미매칭 손실을 막는 crosswalk key로 유지한다.

## G. 테스트 결과

- unit/integration/smoke 30개: 모두 통과
- UI inline JavaScript 문법: 통과
- 기존 SCM dashboard contract: 통과
- SCM 재수집/0판매/거래처 선택: 통과
- YES24 원본 성별·연령·지역 grain: 통과
- 실제 Supabase: 사용자 11, 제품 5,219 로드 통과
- 실제 SCM: 상태/대시보드 조회 통과
- DB 보안 advisor: RLS disabled ERROR, mutable search_path WARN, public SECURITY DEFINER WARN 해소

## H. 향후 권장 순서

1. 마케팅 계획 저장·실행 저장·삭제를 transaction RPC로 이전
2. 현재 DOM/API contract test를 보강한 후 `ui/index.html`을 화면별 모듈로 분리
3. `database.py`를 도메인 repository로 분리하되 `Backend` API 시그니처는 유지
4. 원격 22개 migration을 로컬 baseline에 재구성해 신규 설치 재현성 확보
5. 제품코드 FK 후보의 orphan 검사 후 보존적 constraint 추가

## 적용 migration

- Remote: `20260821204737 system_architecture_security_cleanup`
- Local: `migrations/20260822_system_architecture_security_cleanup.sql`
- DROP/rename/data rewrite: 없음
