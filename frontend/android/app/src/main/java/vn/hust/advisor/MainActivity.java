package vn.hust.advisor;

import android.content.res.Configuration;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowInsetsController;
import android.webkit.JavascriptInterface;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    private boolean mCurrentDark = false;
    private boolean mHasExplicitTheme = false;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Mặc định ban đầu theo theme của hệ điều hành
        int nightMode = getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK;
        mCurrentDark = (nightMode == Configuration.UI_MODE_NIGHT_YES);
        applySystemBars(mCurrentDark);

        // Bridge nhận thông báo thay đổi theme trực tiếp từ React app
        try {
            if (getBridge() != null && getBridge().getWebView() != null) {
                getBridge().getWebView().addJavascriptInterface(new Object() {
                    @JavascriptInterface
                    public void setStatusBarStyle(String style) {
                        runOnUiThread(() -> {
                            mHasExplicitTheme = true;
                            boolean isDark = "dark".equalsIgnoreCase(style);
                            applySystemBars(isDark);
                        });
                    }
                }, "AndroidThemeBridge");
            }
        } catch (Exception e) {
            // fallback
        }
    }

    @Override
    public void onResume() {
        super.onResume();
        applySystemBars(mCurrentDark);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            applySystemBars(mCurrentDark);
        }
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        if (!mHasExplicitTheme) {
            int nightMode = newConfig.uiMode & Configuration.UI_MODE_NIGHT_MASK;
            mCurrentDark = (nightMode == Configuration.UI_MODE_NIGHT_YES);
            applySystemBars(mCurrentDark);
        }
    }

    private void applySystemBars(boolean isDark) {
        mCurrentDark = isDark;
        Window window = getWindow();
        WindowCompat.setDecorFitsSystemWindows(window, false);
        window.setStatusBarColor(Color.TRANSPARENT);
        window.setNavigationBarColor(Color.TRANSPARENT);

        View decorView = window.getDecorView();
        
        // WindowInsetsControllerCompat:
        // isDark = true (nền tối) -> icon sáng/trắng (setAppearanceLightStatusBars(false))
        // isDark = false (nền sáng) -> icon tối/đen (setAppearanceLightStatusBars(true))
        WindowInsetsControllerCompat controller = WindowCompat.getInsetsController(window, decorView);
        if (controller != null) {
            controller.setAppearanceLightStatusBars(!isDark);
            controller.setAppearanceLightNavigationBars(!isDark);
        }

        // Native WindowInsetsController trên Android 11+ (API 30+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            WindowInsetsController insetsController = window.getInsetsController();
            if (insetsController != null) {
                int appearance = !isDark
                    ? (WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS)
                    : 0;
                insetsController.setSystemBarsAppearance(
                    appearance,
                    WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS
                );
            }
        }

        // Đồng bộ cờ legacy
        int flags = decorView.getSystemUiVisibility();
        if (!isDark) {
            flags |= View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
            flags |= View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
        } else {
            flags &= ~View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
            flags &= ~View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
        }
        decorView.setSystemUiVisibility(flags);

        decorView.post(() -> {
            if (controller != null) {
                controller.setAppearanceLightStatusBars(!mCurrentDark);
                controller.setAppearanceLightNavigationBars(!mCurrentDark);
            }
        });
    }
}
