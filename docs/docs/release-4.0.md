# Release 4.0 - AI Producer

## 목표

기사 하나를 보고 유튜브 쇼츠로 제작할 가치가 있는지 AI가 평가한다.

## 입력

- 기사 제목
- 기사 출처
- 기사 본문 또는 정제된 본문

## 출력

- score
- category
- reason
- summary
- script
- youtube_title
- thumbnail_text
- hook

## 평가 기준

- 흥미도
- 희귀성
- 시각성
- 이해도
- 공유성

## 완료 조건

- ProducerService 파일 생성
- producer_prompt.txt 적용
- 기사 1개에 대해 Producer JSON 출력
- output JSON에 producer 결과 포함