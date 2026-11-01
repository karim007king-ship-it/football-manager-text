package org.test.nativediagnostic;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.view.Gravity;
import android.widget.TextView;

public class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        TextView message = new TextView(this);
        message.setText("NATIVE ANDROID TEST\n\nIf this screen stays open, the native Android app started successfully.\n\nNo Kivy, SDL2, or Python is used.");
        message.setTextSize(22);
        message.setTextColor(Color.BLACK);
        message.setGravity(Gravity.CENTER);
        message.setPadding(32, 32, 32, 32);

        setContentView(message);
    }
}
