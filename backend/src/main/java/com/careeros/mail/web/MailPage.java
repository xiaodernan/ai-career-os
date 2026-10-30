package com.careeros.mail.web;

/**
 * The unsubscribe page's markup (roadmap 23.1): one small HTML document, in the reader's
 * language, that shows every dial and posts a change for any of them.
 *
 * <p>There is no template engine in this app and this page is not a reason to add one. Every
 * value written into the markup is server-built -- the action URLs come from {@code MailLinks},
 * which signs them, and they are the only interpolation -- so no reader text reaches the
 * document and there is nothing here to escape. The page ships as UTF-8 bytes with a language
 * attribute so the Chinese copy renders in whatever browser a mailbox opens.
 */
final class MailPage {

    private static final Words EN = new Words(
            "en",
            "Career OS mail settings",
            "Career OS mail settings",
            "These settings decide whether Career OS writes to this address. Every change is "
                    + "saved the moment you press a button; nothing else about your account changes.",
            "The Monday letter",
            "A week of applications, response rates and stalled roles, mailed once every Monday.",
            "The morning signals",
            "Anything waiting in your inbox -- a reminder that came due, a quiet application, a "
                    + "failed pull -- mailed at most once per item.",
            "The reminder's own letter",
            "A reminder you set, mailed the moment it comes due instead of waiting for the "
                    + "morning. Turning this off does not silence the reminder: the morning "
                    + "letter still carries it.",
            "On",
            "Off",
            "Stop",
            "Start",
            "Saved.",
            "This link is the only key to this page. Anyone holding it can change these settings, "
                    + "so treat the mail that carried it the way you would a password; replacing "
                    + "the server's link secret retires every link at once.");

    private static final Words ZH = new Words(
            "zh",
            "Career OS 邮件设置",
            "Career OS 邮件设置",
            "这里的开关决定 Career OS 会不会写信到这个地址。按下按钮即保存，账号的其他部分不受影响。",
            "周一信",
            "每周一寄出一次：这一周的投递、回复率和停滞的职位。",
            "每日信号",
            "收件箱里等你的内容——到期的提醒、安静的投递、失败的抓取——每条最多寄一次。",
            "提醒的即时信",
            "你设的提醒到点那一刻就寄出，而不是等到第二天早上。关掉它不会让提醒消失：每日信号里仍然会有。",
            "开",
            "关",
            "停止",
            "恢复",
            "已保存。",
            "这个链接就是进入本页的唯一钥匙。任何人拿到它都能修改这些设置，请像对待密码一样对待带来它的那封信；更换服务器上的链接密钥会让所有链接同时失效。");

    private MailPage() {
    }

    /**
     * The whole document. {@code pageUrl} is the page's own signed URL; the forms append the
     * action and the list to it. {@code changed} adds the confirmation line for the POST that
     * just happened.
     */
    static String render(String locale, boolean weeklyOn, boolean signalOn, boolean reminderOn,
                         String pageUrl, boolean changed) {
        Words words = wordsFor(locale);
        StringBuilder html = new StringBuilder(2048);
        html.append("<!doctype html>\n<html lang=\"").append(words.lang()).append("\">\n<head>\n")
                .append("<meta charset=\"utf-8\">\n")
                .append("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n")
                .append("<meta name=\"robots\" content=\"noindex\">\n")
                .append("<title>").append(words.title()).append("</title>\n")
                .append("<style>body{font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;")
                .append("max-width:36rem;margin:3rem auto;padding:0 1.25rem;color:#1b1b1b}")
                .append("h1{font-size:1.5rem;margin:0 0 1rem}h2{font-size:1.05rem;margin:0 0 .25rem}")
                .append("p{margin:.25rem 0 1rem}section{border-top:1px solid #ddd;padding:1.25rem 0}")
                .append("button{font:inherit;padding:.45rem 1.1rem;border:1px solid #1b1b1b;")
                .append("border-radius:.4rem;background:#fff;cursor:pointer}")
                .append(".notice{background:#eef7ee;border:1px solid #b7d7b7;padding:.6rem .9rem;")
                .append("border-radius:.4rem}.state{font-weight:600}footer{margin-top:2rem;")
                .append("font-size:.85rem;color:#555}</style>\n</head>\n<body>\n")
                .append("<h1>").append(words.heading()).append("</h1>\n")
                .append("<p>").append(words.intro()).append("</p>\n");
        if (changed) {
            html.append("<p class=\"notice\">").append(words.saved()).append("</p>\n");
        }
        section(html, words.weeklyTitle(), words.weeklyBlurb(), weeklyOn, words,
                pageUrl + "/stop/weekly", pageUrl + "/start/weekly");
        section(html, words.signalTitle(), words.signalBlurb(), signalOn, words,
                pageUrl + "/stop/signals", pageUrl + "/start/signals");
        section(html, words.reminderTitle(), words.reminderBlurb(), reminderOn, words,
                pageUrl + "/stop/reminders", pageUrl + "/start/reminders");
        html.append("<footer>").append(words.keyWarning()).append("</footer>\n</body>\n</html>\n");
        return html.toString();
    }

    private static void section(StringBuilder html, String title, String blurb, boolean on,
                                Words words, String stopUrl, String startUrl) {
        html.append("<section>\n<h2>").append(title).append("</h2>\n")
                .append("<p>").append(blurb).append("</p>\n")
                .append("<p class=\"state\">").append(on ? words.on() : words.off()).append("</p>\n")
                .append("<form method=\"post\" action=\"").append(on ? stopUrl : startUrl).append("\">\n")
                .append("<button type=\"submit\">").append(on ? words.stop() : words.start())
                .append("</button>\n</form>\n</section>\n");
    }

    private static Words wordsFor(String locale) {
        return "zh".equals(locale) ? ZH : EN;
    }

    /** One language's half of the page. */
    record Words(
            String lang,
            String title,
            String heading,
            String intro,
            String weeklyTitle,
            String weeklyBlurb,
            String signalTitle,
            String signalBlurb,
            String reminderTitle,
            String reminderBlurb,
            String on,
            String off,
            String stop,
            String start,
            String saved,
            String keyWarning) {
    }
}
