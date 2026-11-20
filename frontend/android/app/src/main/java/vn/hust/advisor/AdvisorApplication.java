package vn.hust.advisor;

import android.app.Application;
import android.os.Build;
import android.webkit.WebView;

public class AdvisorApplication extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            String processName = getProcessName();
            if (processName != null && processName.endsWith(":ctt_auth")) {
                WebView.setDataDirectorySuffix("ctt_auth");
            }
        }
    }
}
