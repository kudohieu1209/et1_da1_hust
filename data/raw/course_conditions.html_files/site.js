$(document).ready(function () {
    $(window).scroll(function () {
        toogleBackToTopButton();
    });
    $("#btnBackToTop").click(function (event) {
        event.preventDefault();
        $("html, body").animate({ scrollTop: 0 }, '500');
        return false;
    });
});
function toogleBackToTopButton(){
    var offset = 200;
    if($(this).scrollTop() > offset)
        $(".btnBackToTop").removeClass("hidden");
    else
        $(".btnBackToTop").addClass("hidden");
}
