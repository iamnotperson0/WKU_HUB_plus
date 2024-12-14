$(document).ready(function () {
    if (!userEmail) {
        // 로그인하지 않은 경우에만 실행

        // 로그인 팝업 열기
        $('#login-button').click(function () {
            $('#login-popup').show();
        });

        // 로그인 팝업 닫기
        $('#close-login-popup').click(function () {
            $('#login-popup').hide();
        });

        // 로그인 팝업 드래그 가능하게 설정
        $('#login-popup').draggable();

        // 회원가입 링크 클릭 시 로그인 팝업 숨기고 회원가입 페이지로 전환
        $('#signup-link').click(function (event) {
            event.preventDefault(); // 기본 링크 동작을 막음
            $('#login-popup').hide(); // 로그인 팝업 숨기기
            $('#signup-page').show(); // 회원가입 페이지 보여주기
        });

        // 로그인 페이지 링크 클릭 시 회원가입 페이지 숨기고 로그인 팝업 보여주기
        $('#login-link').click(function (event) {
            event.preventDefault(); // 기본 링크 동작을 막음
            $('#signup-page').hide(); // 회원가입 페이지 숨기기
            $('#login-popup').show(); // 로그인 팝업 보여주기
        });
    }
});
