package vn.hust.advisor;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.os.Message;
import android.text.TextUtils;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.webkit.CookieManager;
import android.webkit.SslErrorHandler;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebStorage;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicBoolean;

public class CttLoginActivity extends AppCompatActivity {
    public static final String EXTRA_CTT_COOKIE = "ctt_cookie";
    public static final String EXTRA_USER_AGENT = "user_agent";
    public static final String EXTRA_ERROR = "ctt_error";

    private static final String LOGIN_URL = "https://ctt-sis.hust.edu.vn/Account/Login.aspx";
    private static final String CTT_ORIGIN = "https://ctt-sis.hust.edu.vn";
    private static final String READY_CHECK_JS =
        "(() => {" +
        "  if (location.origin !== 'https://ctt-sis.hust.edu.vn') return false;" +
        "  if (/\\/account\\/(login|logout)\\.aspx/i.test(location.pathname)) return false;" +
        "  if (document.querySelector('input[type=\"password\"]')) return false;" +
        "  return Array.from(document.querySelectorAll('a[href]')).some(a => {" +
        "    try {" +
        "      const target = new URL(a.href, location.href);" +
        "      return target.origin === location.origin && /\\/(account\\/)?logout\\.aspx$/i.test(target.pathname);" +
        "    } catch (e) { return false; }" +
        "  });" +
        "})()";

    private WebView mWebView;
    private ProgressBar mProgressBar;
    private TextView mSubtitleView;
    private String mUserAgent = "";
    private final AtomicBoolean mCompleted = new AtomicBoolean(false);

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        int nightMode = getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK;
        boolean isDark = (nightMode == Configuration.UI_MODE_NIGHT_YES);
        int bgColor = isDark ? Color.parseColor("#18181B") : Color.parseColor("#FFFFFF");
        int barColor = isDark ? Color.parseColor("#202024") : Color.parseColor("#FAF8F5");
        int textColor = isDark ? Color.parseColor("#F4F4F5") : Color.parseColor("#18181B");
        int mutedColor = isDark ? Color.parseColor("#A1A1AA") : Color.parseColor("#52525B");
        int dividerColor = isDark ? Color.parseColor("#27272A") : Color.parseColor("#E4E4E7");
        int accentColor = Color.parseColor("#B91C1C");

        Window window = getWindow();
        WindowCompat.setDecorFitsSystemWindows(window, false);
        window.setStatusBarColor(Color.TRANSPARENT);
        window.setNavigationBarColor(Color.TRANSPARENT);
        WindowInsetsControllerCompat controller = WindowCompat.getInsetsController(window, window.getDecorView());
        if (controller != null) {
            controller.setAppearanceLightStatusBars(!isDark);
            controller.setAppearanceLightNavigationBars(!isDark);
        }

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(bgColor);
        root.setLayoutParams(new ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT
        ));

        LinearLayout topBar = new LinearLayout(this);
        topBar.setOrientation(LinearLayout.HORIZONTAL);
        topBar.setGravity(Gravity.CENTER_VERTICAL);
        topBar.setBackgroundColor(barColor);
        int hPad = dp(8);
        int vPad = dp(6);
        topBar.setPadding(hPad, vPad, hPad, vPad);
        topBar.setMinimumHeight(dp(56));
        topBar.setLayoutParams(new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        ));

        Button closeBtn = createTopButton("Đóng", textColor);
        closeBtn.setContentDescription("Đóng cửa sổ đăng nhập CTT");
        closeBtn.setOnClickListener(v -> {
            setResult(RESULT_CANCELED);
            finish();
        });
        topBar.addView(closeBtn);

        LinearLayout titleBox = new LinearLayout(this);
        titleBox.setOrientation(LinearLayout.VERTICAL);
        titleBox.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams titleParams = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        titleParams.setMargins(dp(8), 0, dp(8), 0);
        titleBox.setLayoutParams(titleParams);

        TextView titleView = new TextView(this);
        titleView.setText("Đăng nhập CTT HUST");
        titleView.setTextColor(textColor);
        titleView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15);
        titleView.setTypeface(null, Typeface.BOLD);
        titleView.setSingleLine(true);
        titleView.setEllipsize(TextUtils.TruncateAt.END);
        titleBox.addView(titleView);

        mSubtitleView = new TextView(this);
        mSubtitleView.setText("ctt-sis.hust.edu.vn");
        mSubtitleView.setTextColor(mutedColor);
        mSubtitleView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        mSubtitleView.setSingleLine(true);
        mSubtitleView.setEllipsize(TextUtils.TruncateAt.END);
        titleBox.addView(mSubtitleView);
        topBar.addView(titleBox);

        Button reloadBtn = createTopButton("Tải lại", accentColor);
        reloadBtn.setContentDescription("Tải lại trang đăng nhập CTT");
        reloadBtn.setOnClickListener(v -> {
            if (mWebView != null) {
                mWebView.reload();
            }
        });
        topBar.addView(reloadBtn);
        root.addView(topBar);

        View divider = new View(this);
        divider.setBackgroundColor(dividerColor);
        divider.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
        root.addView(divider);

        mProgressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        mProgressBar.setMax(100);
        mProgressBar.setVisibility(View.GONE);
        mProgressBar.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(3)));
        root.addView(mProgressBar);

        mWebView = new WebView(this);
        mWebView.setLayoutParams(new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            0,
            1f
        ));
        configureWebView(mWebView);
        root.addView(mWebView);

        setContentView(root);

        ViewCompat.setOnApplyWindowInsetsListener(root, (v, windowInsets) -> {
            Insets bars = windowInsets.getInsets(
                WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout()
            );
            Insets ime = windowInsets.getInsets(WindowInsetsCompat.Type.ime());
            topBar.setPadding(hPad + bars.left, vPad + bars.top, hPad + bars.right, vPad);
            topBar.setMinimumHeight(dp(56) + bars.top);
            v.setPadding(0, 0, 0, Math.max(bars.bottom, ime.bottom));
            return WindowInsetsCompat.CONSUMED;
        });
        ViewCompat.requestApplyInsets(root);

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (mWebView != null && mWebView.canGoBack()) {
                    mWebView.goBack();
                } else {
                    setResult(RESULT_CANCELED);
                    finish();
                }
            }
        });

        startCleanPortalLoad();
    }

    private Button createTopButton(String label, int textColor) {
        Button button = new Button(this, null, android.R.attr.borderlessButtonStyle);
        button.setText(label);
        button.setAllCaps(false);
        button.setTextColor(textColor);
        button.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        button.setMinWidth(0);
        button.setMinimumWidth(0);
        button.setPadding(dp(10), dp(6), dp(10), dp(6));
        return button;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void configureWebView(WebView webView) {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setSupportMultipleWindows(true);
        settings.setJavaScriptCanOpenWindowsAutomatically(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setSavePassword(false);
        settings.setSaveFormData(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

        String ua = settings.getUserAgentString();
        if (ua != null) {
            ua = ua.replace("; wv)", ")").replace("; wv;", ";");
            settings.setUserAgentString(ua);
        }
        mUserAgent = settings.getUserAgentString() != null ? settings.getUserAgentString() : "";

        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(webView, true);

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                if (mProgressBar == null) return;
                if (newProgress >= 100) {
                    mProgressBar.setVisibility(View.GONE);
                } else {
                    mProgressBar.setVisibility(View.VISIBLE);
                    mProgressBar.setProgress(newProgress);
                }
            }

            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, Message resultMsg) {
                if (resultMsg == null || !(resultMsg.obj instanceof WebView.WebViewTransport)) {
                    return false;
                }
                WebView popupWebView = new WebView(CttLoginActivity.this);
                popupWebView.setWebViewClient(new WebViewClient() {
                    @Override
                    public boolean shouldOverrideUrlLoading(WebView popup, WebResourceRequest request) {
                        Uri uri = request != null ? request.getUrl() : null;
                        if (uri != null && "https".equalsIgnoreCase(uri.getScheme()) && mWebView != null) {
                            mWebView.loadUrl(uri.toString());
                        }
                        popup.destroy();
                        return true;
                    }
                });
                WebView.WebViewTransport transport = (WebView.WebViewTransport) resultMsg.obj;
                transport.setWebView(popupWebView);
                resultMsg.sendToTarget();
                return true;
            }
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request != null ? request.getUrl() : null;
                return uri == null || !"https".equalsIgnoreCase(uri.getScheme());
            }

            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.cancel();
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                updateHostSubtitle(url);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                updateHostSubtitle(url);
                if (mCompleted.get() || !isCandidateAuthenticatedCttUrl(url)) {
                    return;
                }
                view.evaluateJavascript(READY_CHECK_JS, value -> {
                    if (!"true".equals(value) || !mCompleted.compareAndSet(false, true)) {
                        return;
                    }
                    CookieManager.getInstance().flush();
                    String cookie = CookieManager.getInstance().getCookie(CTT_ORIGIN);
                    if (cookie == null || cookie.trim().isEmpty()) {
                        mCompleted.set(false);
                        return;
                    }
                    Intent resultIntent = new Intent();
                    resultIntent.putExtra(EXTRA_CTT_COOKIE, cookie);
                    resultIntent.putExtra(EXTRA_USER_AGENT, mUserAgent);
                    setResult(RESULT_OK, resultIntent);
                    finish();
                });
            }
        });
    }

    private void startCleanPortalLoad() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            WebStorage.getInstance().deleteAllData();
            CookieManager.getInstance().removeAllCookies(ignored -> {
                if (mWebView != null && !isFinishing() && !isDestroyed()) {
                    mWebView.loadUrl(LOGIN_URL);
                }
            });
        } else if (mWebView != null) {
            mWebView.loadUrl(LOGIN_URL);
        }
    }

    private void updateHostSubtitle(String url) {
        if (mSubtitleView == null || url == null) return;
        Uri uri = Uri.parse(url);
        String host = uri.getHost();
        if (host != null && !host.isEmpty()) {
            mSubtitleView.setText(host);
        }
    }

    private static boolean isCandidateAuthenticatedCttUrl(String url) {
        if (url == null) return false;
        Uri uri = Uri.parse(url);
        if (!"https".equalsIgnoreCase(uri.getScheme())) return false;
        String host = uri.getHost();
        if (host == null || !"ctt-sis.hust.edu.vn".equalsIgnoreCase(host)) return false;
        String path = uri.getPath();
        if (path == null) return true;
        String lowerPath = path.toLowerCase(Locale.ROOT);
        return !lowerPath.matches(".*/account/(login|logout)\\.aspx$");
    }

    @Override
    protected void onDestroy() {
        if (mWebView != null) {
            ViewGroup parent = (ViewGroup) mWebView.getParent();
            if (parent != null) {
                parent.removeView(mWebView);
            }
            mWebView.stopLoading();
            mWebView.setWebChromeClient(null);
            mWebView.destroy();
            mWebView = null;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            CookieManager cookieManager = CookieManager.getInstance();
            cookieManager.removeAllCookies(null);
            cookieManager.flush();
            WebStorage.getInstance().deleteAllData();
        }
        super.onDestroy();
    }
}
