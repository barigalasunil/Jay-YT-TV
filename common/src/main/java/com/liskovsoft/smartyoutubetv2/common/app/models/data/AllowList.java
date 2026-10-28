package com.liskovsoft.smartyoutubetv2.common.app.models.data;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * KidTube: the single source of truth for what may be shown/played.
 *
 * The list lives in <code>channels.json</code> in your GitHub repo:
 * <pre>
 * {"version":1,
 *  "channels":[{"name":"Peppa Pig","id":"UCxxxxxxxxxxxxxxxxxxxxxx"}],
 *  "songs":[{"title":"Some song","id":"dQw4w9WgXcQ"}]}
 * </pre>
 * Load order: last good downloaded copy -> bundled copy in assets.
 * A fresh copy is downloaded in the background at every app start.
 */
public final class AllowList {
    private static final String TAG = AllowList.class.getSimpleName();

    /** Master switch. When true: no search, no recommendations, only allow-listed content. */
    public static final boolean LOCKDOWN = true;

    /**
     * If a video's channel can't be determined, allow it (true) or block it (false).
     * Videos opened from your own channel/song rows always have a known channel or id,
     * so "true" only matters for odd entry points (cast, deep links).
     */
    public static final boolean ALLOW_UNKNOWN_CHANNEL = true;

    /** The GitHub workflow replaces this with "owner/repo" automatically. Edit by hand for local builds. */
    public static final String REPO = "YOUR_GITHUB_USER/YOUR_REPO";
    private static final String REMOTE_URL = "https://raw.githubusercontent.com/" + REPO + "/HEAD/channels.json";

    /** Reserved section id for the Songs section (pinned ids are > 100). */
    public static final int SONGS_SECTION_ID = 777_001;

    private static final String CACHE_FILE = "allowlist_cache.json";
    private static final String ASSET_FILE = "channels.json";

    public static final class Channel {
        public final String id;
        public final String name;

        Channel(String id, String name) {
            this.id = id;
            this.name = name;
        }
    }

    public static final class Song {
        public final String id;
        public final String title;

        Song(String id, String title) {
            this.id = id;
            this.title = title;
        }
    }

    private static AllowList sInstance;

    private final Context mContext;
    private volatile List<Channel> mChannels = Collections.emptyList();
    private volatile List<Song> mSongs = Collections.emptyList();
    private volatile Set<String> mChannelIds = Collections.emptySet();
    private volatile Set<String> mSongIds = Collections.emptySet();
    private volatile String mRawJson;
    private boolean mRefreshRunning;

    public static synchronized AllowList instance(Context context) {
        if (sInstance == null) {
            sInstance = new AllowList(context.getApplicationContext());
        }
        return sInstance;
    }

    private AllowList(Context context) {
        mContext = context;
        loadLocal();
    }

    // ------------------------------------------------------------------ queries

    public List<Channel> getChannels() {
        return mChannels;
    }

    public List<Song> getSongs() {
        return mSongs;
    }

    public boolean isSongId(String videoId) {
        return videoId != null && mSongIds.contains(videoId);
    }

    public boolean isChannelAllowed(String channelId) {
        return channelId != null && mChannelIds.contains(channelId);
    }

    /**
     * Cheap check used before a video is opened or loaded.
     * Songs are allowed by video id; everything else needs an allowed channel id.
     */
    public boolean isVideoAllowed(String videoId, String channelId) {
        if (!LOCKDOWN) {
            return true;
        }
        if (isSongId(videoId) || isChannelAllowed(channelId)) {
            return true;
        }
        return channelId == null && ALLOW_UNKNOWN_CHANNEL;
    }

    public boolean isVideoAllowed(Video video) {
        return video == null || isVideoAllowed(video.videoId, video.channelId);
    }

    /** Builds the card items for the Songs section, in the order of the JSON file. */
    public List<Video> createSongVideos() {
        List<Video> result = new ArrayList<>();
        for (Song song : mSongs) {
            result.add(createSongVideo(song));
        }
        return result;
    }

    /** Next song after the given video id (wraps around). Null if the id is not a song. */
    public Video findNextSong(String videoId) {
        List<Song> songs = mSongs;
        for (int i = 0; i < songs.size(); i++) {
            if (songs.get(i).id.equals(videoId)) {
                return createSongVideo(songs.get((i + 1) % songs.size()));
            }
        }
        return null;
    }

    private Video createSongVideo(Song song) {
        Video video = Video.from(song.id);
        video.title = song.title;
        video.cardImageUrl = "https://i.ytimg.com/vi/" + song.id + "/hqdefault.jpg";
        return video;
    }

    // ------------------------------------------------------------------ loading

    private void loadLocal() {
        // 1. Last good downloaded copy
        try {
            File cache = new File(mContext.getFilesDir(), CACHE_FILE);
            if (cache.exists()) {
                String json = readAll(new FileInputStream(cache));
                if (apply(json)) {
                    return;
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Can't read cached allow-list: " + e);
        }

        // 2. Copy bundled inside the APK
        try {
            String json = readAll(mContext.getAssets().open(ASSET_FILE));
            apply(json);
        } catch (Exception e) {
            Log.e(TAG, "Can't read bundled allow-list: " + e);
        }
    }

    /**
     * Downloads the newest channels.json in the background.
     * @param onChanged called on the main thread only when the list actually changed
     */
    public void refreshAsync(Runnable onChanged) {
        if (REPO.startsWith("YOUR_")) {
            Log.w(TAG, "REPO is not configured. Using bundled list only.");
            return;
        }

        synchronized (this) {
            if (mRefreshRunning) {
                return;
            }
            mRefreshRunning = true;
        }

        new Thread(() -> {
            try {
                String json = download(REMOTE_URL);
                String before = mRawJson;

                if (apply(json)) {
                    saveCache(json);
                    if (before == null || !before.equals(json)) {
                        if (onChanged != null) {
                            new Handler(Looper.getMainLooper()).post(onChanged);
                        }
                    }
                }
            } catch (Exception e) {
                Log.e(TAG, "Can't download allow-list (staying with the cached one): " + e);
            } finally {
                synchronized (AllowList.this) {
                    mRefreshRunning = false;
                }
            }
        }, "AllowListRefresh").start();
    }

    private boolean apply(String json) {
        try {
            JSONObject root = new JSONObject(json);

            List<Channel> channels = new ArrayList<>();
            Set<String> channelIds = new HashSet<>();
            JSONArray ch = root.optJSONArray("channels");
            if (ch != null) {
                for (int i = 0; i < ch.length(); i++) {
                    JSONObject o = ch.optJSONObject(i);
                    if (o == null) {
                        continue;
                    }
                    String id = o.optString("id", "").trim();
                    // Real channel ids look like UCxxxxxxxxxxxxxxxxxxxxxx. Skips the example/placeholder rows.
                    if (!id.startsWith("UC") || id.length() < 20) {
                        continue;
                    }
                    channels.add(new Channel(id, o.optString("name", id)));
                    channelIds.add(id);
                }
            }

            List<Song> songs = new ArrayList<>();
            Set<String> songIds = new HashSet<>();
            JSONArray so = root.optJSONArray("songs");
            if (so != null) {
                for (int i = 0; i < so.length(); i++) {
                    JSONObject o = so.optJSONObject(i);
                    if (o == null) {
                        continue;
                    }
                    String id = o.optString("id", "").trim();
                    if (id.length() != 11) {
                        continue;
                    }
                    songs.add(new Song(id, o.optString("title", id)));
                    songIds.add(id);
                }
            }

            mChannels = Collections.unmodifiableList(channels);
            mChannelIds = channelIds;
            mSongs = Collections.unmodifiableList(songs);
            mSongIds = songIds;
            mRawJson = json;
            return true;
        } catch (Exception e) {
            Log.e(TAG, "Bad channels.json: " + e);
            return false;
        }
    }

    private void saveCache(String json) {
        try {
            File dir = mContext.getFilesDir();
            File tmp = new File(dir, CACHE_FILE + ".tmp");
            try (FileOutputStream out = new FileOutputStream(tmp)) {
                out.write(json.getBytes(StandardCharsets.UTF_8));
            }
            File target = new File(dir, CACHE_FILE);
            if (!tmp.renameTo(target)) {
                target.delete();
                tmp.renameTo(target);
            }
        } catch (Exception e) {
            Log.e(TAG, "Can't save allow-list cache: " + e);
        }
    }

    private static String download(String url) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
        conn.setConnectTimeout(8_000);
        conn.setReadTimeout(8_000);
        conn.setUseCaches(false);
        conn.setRequestProperty("Cache-Control", "no-cache");
        try {
            if (conn.getResponseCode() != 200) {
                throw new IllegalStateException("HTTP " + conn.getResponseCode());
            }
            return readAll(conn.getInputStream());
        } finally {
            conn.disconnect();
        }
    }

    private static String readAll(InputStream in) throws Exception {
        try (InputStream is = in) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int n;
            while ((n = is.read(buf)) != -1) {
                out.write(buf, 0, n);
            }
            return new String(out.toByteArray(), StandardCharsets.UTF_8);
        }
    }
}
