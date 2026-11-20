package vn.hust.advisor;

import android.app.Activity;
import android.content.Intent;
import androidx.activity.result.ActivityResult;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "CttPortal")
public class CttPortalPlugin extends Plugin {
    @PluginMethod
    public void openLogin(PluginCall call) {
        Intent intent = new Intent(getContext(), CttLoginActivity.class);
        startActivityForResult(call, intent, "handleLoginResult");
    }

    @ActivityCallback
    private void handleLoginResult(PluginCall call, ActivityResult result) {
        if (call == null) {
            return;
        }
        int resultCode = result.getResultCode();
        Intent data = result.getData();
        if (resultCode == Activity.RESULT_OK && data != null) {
            String cookie = data.getStringExtra(CttLoginActivity.EXTRA_CTT_COOKIE);
            String userAgent = data.getStringExtra(CttLoginActivity.EXTRA_USER_AGENT);
            if (cookie == null || cookie.trim().isEmpty()) {
                call.reject("Không đọc được phiên đăng nhập CTT.");
                return;
            }
            JSObject ret = new JSObject();
            ret.put("cookie", cookie);
            if (userAgent != null && !userAgent.isEmpty()) {
                ret.put("userAgent", userAgent);
            }
            call.resolve(ret);
            return;
        }
        if (resultCode == Activity.RESULT_CANCELED) {
            call.reject("Đã hủy đăng nhập CTT.", "CANCELLED");
            return;
        }
        String err = data != null ? data.getStringExtra(CttLoginActivity.EXTRA_ERROR) : null;
        call.reject(err != null && !err.isEmpty() ? err : "Không hoàn tất được đăng nhập CTT.");
    }
}
