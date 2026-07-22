from __future__ import annotations


CATEGORY_LABELS = {
    "mystery": "미스터리",
    "science": "과학",
    "history": "역사",
    "space": "우주",
}

ALL_CATEGORY_LABEL = "전체 자동"

SOURCE_MODE_LABELS = {
    "mixed": "최신 + 미스터리 아카이브",
    "trend": "최신 화제",
    "archive": "미스터리 아카이브",
}


CATEGORY_QUERIES = {
    "mystery": (
        "미스터리 발견 정체",
        "고대 유적 새로운 발견",
        "미확인 현상 과학적 분석",
    ),
    "science": (
        "과학 새로운 발견 연구",
        "인류 자연 최신 연구",
        "기후 생명 과학 발견",
    ),
    "history": (
        "역사 유적 발굴 발견",
        "고대 문명 새로운 연구",
        "고고학 무덤 유물 발견",
    ),
    "space": (
        "우주 천문학 새로운 발견",
        "NASA 행성 관측 연구",
        "블랙홀 외계 생명 탐사",
    ),
}


CATEGORY_KEYWORDS = {
    "mystery": {
        "미스터리",
        "정체",
        "미확인",
        "수수께끼",
        "비밀",
        "의문",
        "불가사의",
        "실종",
        "심해",
        "유적",
        "암호",
    },
    "science": {
        "과학",
        "연구",
        "발견",
        "실험",
        "생명",
        "기후",
        "진화",
        "물리",
        "뇌",
        "유전자",
        "공룡",
    },
    "history": {
        "역사",
        "고대",
        "유적",
        "발굴",
        "문명",
        "왕조",
        "무덤",
        "유물",
        "고고학",
        "제국",
        "기록",
    },
    "space": {
        "우주",
        "행성",
        "별",
        "은하",
        "블랙홀",
        "NASA",
        "천문",
        "화성",
        "달",
        "외계",
        "소행성",
    },
}


CHANNEL_FIT_KEYWORDS = {
    "mystery": {
        "고대",
        "유적",
        "미라",
        "우주",
        "행성",
        "UFO",
        "심해",
        "문명",
        "무덤",
        "고고학",
        "과학",
        "역사",
        "화성",
        "암호",
        "해저",
        "청동",
        "3천년",
        "천문",
    },
    "science": {
        "과학",
        "연구",
        "실험",
        "생명",
        "기후",
        "진화",
        "물리",
        "뇌",
        "유전자",
        "공룡",
        "자연",
        "의학",
        "에너지",
    },
    "history": {
        "역사",
        "고대",
        "유적",
        "발굴",
        "문명",
        "왕조",
        "무덤",
        "유물",
        "고고학",
        "제국",
        "청동",
        "세기",
    },
    "space": {
        "우주",
        "행성",
        "은하",
        "블랙홀",
        "NASA",
        "천문",
        "화성",
        "달",
        "외계",
        "소행성",
        "태양",
        "별",
    },
}


HOOK_KEYWORDS = {
    "최초",
    "새로운",
    "발견",
    "정체",
    "비밀",
    "미스터리",
    "왜",
    "실제로",
    "사라진",
    "풀렸다",
    "밝혀졌다",
    "뒤집은",
}


VISUAL_KEYWORDS = {
    "사진",
    "영상",
    "발견",
    "발굴",
    "유적",
    "무덤",
    "행성",
    "우주",
    "심해",
    "공룡",
    "미라",
    "유물",
}


EXCLUDE_KEYWORDS = {
    "대통령",
    "국회",
    "정당",
    "선거",
    "주가",
    "코스피",
    "연예인",
    "열애",
    "살인",
    "사망 사고",
    "실화탐사대",
    "아파트 주민",
    "연쇄 낙서",
    "도심 낙서",
    "범인 정체",
}


# 채널 주제와 일부 단어가 겹쳐도 게임·엔터테인먼트 소식은 제외합니다.
BRAND_EXCLUDE_KEYWORDS = {
    "게임",
    "패치",
    "업데이트",
    "출시",
    "시즌",
    "e스포츠",
    "드라마",
    "영화",
    "웹툰",
    "애니메이션",
    "리뷰",
    "플레이",
    "코로나",
    "바이러스",
    "균주",
    "질환",
    "치료제",
    "환자",
    "병원",
    "심포지엄",
}


TOPIC_MATCH_STOPWORDS = {
    "고대",
    "최근",
    "새로운",
    "발견",
    "연구",
    "정체",
    "비밀",
    "미스터리",
    "사실",
    "이유",
    "무엇",
    "어떻게",
}


TRUSTED_SOURCE_KEYWORDS = {
    "연합뉴스",
    "뉴시스",
    "동아일보",
    "동아사이언스",
    "과학동아",
    "지디넷코리아",
    "BBC",
    "Reuters",
    "AP",
    "NASA",
    "Nature",
    "Science",
    "Smithsonian",
    "National Geographic",
}


LOW_QUALITY_SOURCE_KEYWORDS = {
    "Vietnam.vn",
}


SENSATIONAL_KEYWORDS = {
    "충격",
    "경악",
    "소름",
    "발칵",
    "!",
}


FALLBACK_TOPICS = {
    "mystery": (
        "보이니치 문서는 왜 아직도 해독되지 않았을까",
        "안티키테라 장치는 어떻게 시대를 앞섰을까",
        "나스카 라인은 누가 무엇을 위해 만들었을까",
        "디아틀로프 고개 사건의 가장 현실적인 설명",
        "메리 셀레스트호에서는 무슨 일이 있었을까",
        "로어노크 식민지 사람들은 어디로 사라졌을까",
        "발트해 해저 원형 구조물의 정체",
        "사하라의 거대한 눈은 어떻게 만들어졌을까",
        "심해에서 들린 정체불명의 소리 블룹의 진실",
        "버뮤다 삼각지대 실종 기록은 사실일까",
    ),
    "science": (
        "지구 생명체는 왜 잠을 자야 할까",
        "물곰은 어떻게 우주에서도 살아남을까",
        "인간의 뇌는 죽기 직전 무엇을 경험할까",
        "공룡을 멸종시킨 날 지구에서는 무슨 일이 있었을까",
        "문어의 지능은 왜 독립적으로 진화했을까",
        "지구 내부에는 얼마나 많은 물이 숨어 있을까",
        "암흑물질은 정말 존재할까",
        "노화는 치료 가능한 현상이 될 수 있을까",
        "균류 네트워크는 숲에서 어떤 정보를 전달할까",
        "지구 자기장이 뒤집히면 어떤 일이 생길까",
    ),
    "history": (
        "고대 이집트인은 왜 미라에 황금 혀를 넣었을까",
        "로마 콘크리트는 왜 2천 년을 버틸까",
        "폼페이 최후의 하루에는 무슨 일이 있었을까",
        "괴베클리 테페는 인류 역사를 어떻게 바꿨을까",
        "알렉산드리아 도서관에는 무엇이 있었을까",
        "진시황 병마용에는 왜 서로 다른 얼굴이 있을까",
        "바이킹은 콜럼버스보다 먼저 아메리카에 갔을까",
        "고대인은 스톤헨지의 돌을 어떻게 옮겼을까",
        "마야 문명은 왜 거대한 도시를 버렸을까",
        "잉카인은 문자 없이 거대한 제국을 어떻게 운영했을까",
    ),
    "space": (
        "우주는 왜 완전히 조용할까",
        "블랙홀 안으로 들어가면 무엇을 보게 될까",
        "목성의 위성 유로파 바다에 생명체가 있을까",
        "화성은 어떻게 물을 잃어버렸을까",
        "우주에는 왜 외계 문명의 흔적이 보이지 않을까",
        "중성자별 한 숟가락은 얼마나 무거울까",
        "태양이 갑자기 사라지면 지구는 언제 알게 될까",
        "달 뒷면은 왜 지구에서 볼 수 없을까",
        "우주의 끝에는 무엇이 있을까",
        "떠돌이 행성에는 생명체가 살 수 있을까",
    ),
}


# 외부 위키는 아이디어 발견에만 사용하고, 실제 영상 조사는 공식·학술 자료로
# 다시 검증합니다. 현재 검수된 상시 관심 후보를 아카이브의 첫 데이터로 사용합니다.
ARCHIVE_TOPICS = FALLBACK_TOPICS


# 검수된 아카이브 주제를 공개 영문 자료·학술 색인·이미지 저장소에서
# 바로 찾을 수 있도록 주제별 핵심 영문 검색어를 함께 보관합니다.
ARCHIVE_RESEARCH_TERMS = {
    "안티키테라 장치는 어떻게 시대를 앞섰을까": "Antikythera mechanism ancient Greek astronomical computer",
    "나스카 라인은 누가 무엇을 위해 만들었을까": "Nazca Lines purpose archaeology Peru",
    "디아틀로프 고개 사건의 가장 현실적인 설명": "Dyatlov Pass incident scientific avalanche explanation",
    "로어노크 식민지 사람들은 어디로 사라졌을까": "Roanoke Colony disappearance archaeology",
    "사하라의 거대한 눈은 어떻게 만들어졌을까": "Richat Structure formation geology",
    "지구 생명체는 왜 잠을 자야 할까": "sleep evolution biological function",
    "공룡을 멸종시킨 날 지구에서는 무슨 일이 있었을까": "Chicxulub impact dinosaur extinction evidence",
    "문어의 지능은 왜 독립적으로 진화했을까": "octopus intelligence cephalopod cognition evolution",
    "지구 내부에는 얼마나 많은 물이 숨어 있을까": "water in Earth mantle ringwoodite",
    "지구 자기장이 뒤집히면 어떤 일이 생길까": "geomagnetic reversal effects evidence",
    "로마 콘크리트는 왜 2천 년을 버틸까": "Roman concrete durability self healing lime clasts",
    "폼페이 최후의 하루에는 무슨 일이 있었을까": "Pompeii eruption 79 CE archaeology",
    "괴베클리 테페는 인류 역사를 어떻게 바꿨을까": "Gobekli Tepe archaeology Neolithic",
    "진시황 병마용에는 왜 서로 다른 얼굴이 있을까": "Terracotta Army individual faces archaeology",
    "바이킹은 콜럼버스보다 먼저 아메리카에 갔을까": "Norse settlement North America L'Anse aux Meadows",
    "고대인은 스톤헨지의 돌을 어떻게 옮겼을까": "Stonehenge stone transport archaeology",
    "마야 문명은 왜 거대한 도시를 버렸을까": "Classic Maya collapse drought archaeology",
    "목성의 위성 유로파 바다에 생명체가 있을까": "Europa subsurface ocean astrobiology",
    "화성은 어떻게 물을 잃어버렸을까": "Mars atmospheric water loss MAVEN",
    "중성자별 한 숟가락은 얼마나 무거울까": "neutron star density mass",
    "태양이 갑자기 사라지면 지구는 언제 알게 될까": "Sun light travel time Earth gravity thought experiment",
    "달 뒷면은 왜 지구에서 볼 수 없을까": "Moon tidal locking far side",
    "떠돌이 행성에는 생명체가 살 수 있을까": "rogue planet habitability astrobiology",
}
