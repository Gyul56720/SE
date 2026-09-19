/* Vitis HLS 내부 매크로 보충.
   공개 저장소 헤더에는 없고 Vitis HLS 설치본의 전처리기 정의로만 들어온다.
   의미는 "이 파라미터는 합성에서 안 쓰인다"이므로 (void) 캐스트면 충분하다. */
#ifndef HLS_COMPAT_H_
#define HLS_COMPAT_H_
#ifndef _AP_UNUSED_PARAM
#define _AP_UNUSED_PARAM(x) ((void)(x))
#endif
#endif
