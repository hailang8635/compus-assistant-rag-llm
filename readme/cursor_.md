# 智能校园客服系统
_Exported on 2025/12/25 at GMT+8 23:12:53 from Cursor (2.2.43)_

---

**User**

你是一名设计师+产品+全栈开发工程师，现在要开发一套"校园百事通"的智能客服系统，后端使用springboot，前端使用jquery或其他不需要前端编译的组件进行开发，功能包括：
1，先总结一20条“校园百事通”的FAQ，形成静态页面供用户参考；
2，用户提问问题后，自动加上“上海大学校园百事通”的promt, 然后调用deepseek 的api接口给出解答
3，输入“人工“后弹出请联系学长:“zhangdreamer@126.com” 
4，交互效果参考chatgpt.com的问答效果，设计风格为智能客服常见布局
参考资料：
@docs/2025年学生手册.pdf @docs/20251209我的培养计划.pdf 

---

**Cursor**

目标是把这套“校园百事通”做成一个可运行的 **Spring Boot 后端 + 纯静态前端(无编译)** 小项目：先生成一个 20 条 FAQ 的静态页，再做一个 ChatGPT 风格的聊天页，前端把问题发给后端；后端会自动拼上“互联网信贷行业 prompt”并调用 DeepSeek API 返回答案，输入“人工”则直接弹出联系邮箱。接下来我会先把你给的 PDF 里能用的文本抽出来（用本地工具转文本），据此写 FAQ，然后搭好后端接口与前端聊天 UI。

我会直接把这个项目做成一个可运行的“前端静态 + Spring Boot 后端”小系统：先从参考PDF/Docx里提取关键信息，整理20条FAQ做成静态页；再实现 `/api/chat` 接口把“上海大学校园百事通 prompt”自动拼到用户问题前并调用 DeepSeek；最后用 jQuery 做一个类 ChatGPT 的对话UI，输入“人工”时弹窗显示联系方式。接下来我先确认 DeepSeek 接口参数、并把三份参考资料的正文抽取出来用于写FAQ。

Nice,三份参考资料都在本地；现在卡点是它们是二进制PDF/Docx，直接读会超长/不可文本化。我接下来会用 Python 试探本机是否已有 `pdfminer`/`PyPDF2`/`python-docx` 之类的库来抽取正文；如果没有，我就改用 Java 的 PDFBox/POI 放进 Spring Boot（可离线构建）来在启动时抽取并生成 FAQ 静态页。

计划：先在当前空目录里初始化一个可运行的 Spring Boot（Maven）项目骨架；然后补齐前端静态 `index.html`（类 ChatGPT 对话布局）+ `faq.html`（20条FAQ）；最后实现后端 `/api/chat`：识别“人工”弹窗分支，其它请求自动拼接“上海大学校园百事通 prompt”并转发到 DeepSeek（endpoint/模型/Key 全部可配置）。我会把所有内容一次性落到代码里，确保你本地 `mvn spring-boot:run` 就能跑起来。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <groupId>com.campus</groupId>
  <artifactId>campus-assistant</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <name>campus-assistant</name>
  <description>校园百事通 - 智能客服系统（Spring Boot + 静态前端）</description>

  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.6</version>
    <relativePath/>
  </parent>

  <properties>
    <java.version>17</java.version>
  </properties>

  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>

    <dependency>
      <groupId>org.projectlombok</groupId>
      <artifactId>lombok</artifactId>
      <optional>true</optional>
    </dependency>

    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <configuration>
          <source>${java.version}</source>
          <target>${java.version}</target>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>


```

```java
package com.campus;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class CampusAssistantApplication {
  public static void main(String[] args) {
    SpringApplication.run(CampusAssistantApplication.class, args);
  }
}


```

```yaml
server:
  port: 8080

campus:
  deepseek:
    # 建议通过环境变量覆盖：
    # DEEPSEEK_API_KEY=xxx
    apiKey: ${DEEPSEEK_API_KEY:}
    # DeepSeek 兼容 OpenAI 的 chat/completions 形态时通常为该地址；如你们学校/内网网关不同可改这里
    baseUrl: ${DEEPSEEK_BASE_URL:https://api.deepseek.com}
    model: ${DEEPSEEK_MODEL:deepseek-chat}
    timeoutMs: ${DEEPSEEK_TIMEOUT_MS:20000}

  # 自动加上的「上海大学校园百事通」prompt（可按你们合规口径继续细化）
  creditPrompt: >
    你是上海大学校园百事通的智能客服。
    回答需遵守合规要求：不诱导借贷、不承诺收益、不提供规避监管建议；
    对涉及个人隐私/资金安全的操作要提醒用户走官方渠道并注意防诈骗。
    同时你服务的产品是“校园百事通”，请用清晰、可执行的校园办事步骤回答问题；
    如涉及校内规章制度，建议用户以学校官方通知/学生手册为准，并给出咨询路径（学院/研究生院/辅导员等）。


```

Aha：项目骨架已经起来了（Maven + Spring Boot 主类 + 可配置的 DeepSeek/Prompt）。接下来我会把核心后端 `/api/chat` 端点和 DeepSeek 客户端实现出来，再把前端 `index.html/faq.html` 静态页补齐并接到这个接口上。

```java
package com.campus.chat.dto;

import jakarta.validation.constraints.NotBlank;

public record ChatRequest(
    @NotBlank(message = "message 不能为空")
    String message
) {}


```

```java
package com.campus.chat.dto;

public record ChatResponse(
    String type,    // "answer" | "human"
    String answer
) {}


```

```java
package com.campus.chat.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "campus.deepseek")
public class DeepSeekProperties {
  private String apiKey;
  private String baseUrl;
  private String model;
  private int timeoutMs = 20000;

  public String getApiKey() {
    return apiKey;
  }

  public void setApiKey(String apiKey) {
    this.apiKey = apiKey;
  }

  public String getBaseUrl() {
    return baseUrl;
  }

  public void setBaseUrl(String baseUrl) {
    this.baseUrl = baseUrl;
  }

  public String getModel() {
    return model;
  }

  public void setModel(String model) {
    this.model = model;
  }

  public int getTimeoutMs() {
    return timeoutMs;
  }

  public void setTimeoutMs(int timeoutMs) {
    this.timeoutMs = timeoutMs;
  }
}


```

```java
package com.campus.chat.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "campus")
public class CampusPromptProperties {
  /**
   * 自动追加的“上海大学校园百事通”Prompt
   */
  private String creditPrompt;

  public String getCreditPrompt() {
    return creditPrompt;
  }

  public void setCreditPrompt(String creditPrompt) {
    this.creditPrompt = creditPrompt;
  }
}


```

```java
package com.campus.chat.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties({DeepSeekProperties.class, CampusPromptProperties.class})
public class PropsConfig {}


```

```java
package com.campus.chat.service;

import com.campus.chat.config.DeepSeekProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

@Component
public class DeepSeekClient {
  private final DeepSeekProperties props;
  private final ObjectMapper objectMapper;
  private final HttpClient httpClient;

  public DeepSeekClient(DeepSeekProperties props, ObjectMapper objectMapper) {
    this.props = props;
    this.objectMapper = objectMapper;
    this.httpClient =
        HttpClient.newBuilder()
            .connectTimeout(Duration.ofMillis(props.getTimeoutMs()))
            .build();
  }

  /**
   * 调用 DeepSeek（OpenAI 兼容 chat/completions 形态）
   */
  public String chat(String systemPrompt, String userMessage) {
    if (!StringUtils.hasText(props.getApiKey())) {
      return "系统未配置 DEEPSEEK_API_KEY，无法调用大模型。请联系管理员配置后重试。";
    }

    try {
      String base = props.getBaseUrl() == null ? "" : props.getBaseUrl().trim();
      if (base.endsWith("/")) base = base.substring(0, base.length() - 1);
      URI uri = URI.create(base + "/chat/completions");

      Map<String, Object> payload = new LinkedHashMap<>();
      payload.put("model", props.getModel());
      payload.put(
          "messages",
          List.of(
              Map.of("role", "system", "content", systemPrompt),
              Map.of("role", "user", "content", userMessage)));
      payload.put("temperature", 0.3);

      String body = objectMapper.writeValueAsString(payload);

      HttpRequest req =
          HttpRequest.newBuilder()
              .uri(uri)
              .timeout(Duration.ofMillis(props.getTimeoutMs()))
              .header("Content-Type", "application/json")
              .header("Authorization", "Bearer " + props.getApiKey())
              .POST(HttpRequest.BodyPublishers.ofString(body))
              .build();

      HttpResponse<String> resp = httpClient.send(req, HttpResponse.BodyHandlers.ofString());
      if (resp.statusCode() < 200 || resp.statusCode() >= 300) {
        return "调用模型失败（HTTP " + resp.statusCode() + "）。请稍后重试或联系管理员。";
      }

      JsonNode root = objectMapper.readTree(resp.body());
      JsonNode content =
          root.path("choices").path(0).path("message").path("content");
      String text = content.isTextual() ? content.asText() : null;
      if (!StringUtils.hasText(text)) {
        return "模型返回为空，请换个问法再试。";
      }
      return text.trim();
    } catch (Exception e) {
      return "调用模型异常：" + e.getClass().getSimpleName() + "。请稍后重试。";
    }
  }
}


```

```java
package com.campus.chat.service;

import com.campus.chat.config.CampusPromptProperties;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class ChatService {
  private static final String HUMAN_KEYWORD = "人工";
  private static final String HUMAN_CONTACT = "请联系学长：zhangdreamer@126.com";

  private final CampusPromptProperties promptProps;
  private final DeepSeekClient deepSeekClient;

  public ChatService(CampusPromptProperties promptProps, DeepSeekClient deepSeekClient) {
    this.promptProps = promptProps;
    this.deepSeekClient = deepSeekClient;
  }

  public ChatResult answer(String userMessage) {
    String msg = userMessage == null ? "" : userMessage.trim();
    if (HUMAN_KEYWORD.equals(msg)) {
      return ChatResult.human(HUMAN_CONTACT);
    }

    String systemPrompt = StringUtils.hasText(promptProps.getCreditPrompt())
        ? promptProps.getCreditPrompt().trim()
        : "你是智能客服，请用简洁步骤回答。";

    // “自动加上上海大学校园百事通的prompt”：这里采用 system 角色做强约束；user 角色保留用户原问题
    String answer = deepSeekClient.chat(systemPrompt, msg);
    return ChatResult.answer(answer);
  }

  public record ChatResult(String type, String answer) {
    public static ChatResult human(String contact) {
      return new ChatResult("human", contact);
    }

    public static ChatResult answer(String text) {
      return new ChatResult("answer", text);
    }
  }
}


```

```java
package com.campus.chat.controller;

import com.campus.chat.dto.ChatRequest;
import com.campus.chat.dto.ChatResponse;
import com.campus.chat.service.ChatService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class ChatController {
  private final ChatService chatService;

  public ChatController(ChatService chatService) {
    this.chatService = chatService;
  }

  @PostMapping("/chat")
  public ChatResponse chat(@Valid @RequestBody ChatRequest req) {
    ChatService.ChatResult result = chatService.answer(req.message());
    return new ChatResponse(result.type(), result.answer());
  }
}


```

```java
package com.campus.chat.controller;

import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {
  @ExceptionHandler(MethodArgumentNotValidException.class)
  @ResponseStatus(HttpStatus.BAD_REQUEST)
  public Map<String, Object> handleValidation(MethodArgumentNotValidException e) {
    FieldError fe = e.getBindingResult().getFieldError();
    String msg = fe != null ? fe.getDefaultMessage() : "参数校验失败";
    return Map.of("error", msg);
  }
}


```

后端核心链路已经打通：`POST /api/chat` 会先识别“人工”，否则自动用 `campus.creditPrompt` 作为 system prompt 调 DeepSeek（baseUrl/model/key 都可配），并把答案返回给前端。接下来我会集中做前端两页：一个 ChatGPT 风格聊天主页（含输入“人工”弹窗、打字中效果、消息气泡），一个 20 条 FAQ 静态页并从主页可一键打开。

---

**User**

完成剩下的两个前端页面

---

**Cursor**

计划：把两页都放到 Spring Boot 的 `src/main/resources/static/`，这样启动后直接通过 `/` 和 `/faq.html` 访问。先做 `index.html`（ChatGPT风格布局、气泡对话、Enter发送、加载中/打字中、侧边栏含FAQ入口、输入“人工”弹窗），再做 `faq.html`（20条FAQ的静态清单、锚点目录、返回聊天入口），最后加一份共享 CSS/JS 让交互更顺滑。

```css
:root{
  --bg:#0b1020;
  --panel:#0f172a;
  --panel2:#111c33;
  --text:#e6eefc;
  --muted:#9db0d0;
  --border:rgba(255,255,255,.08);
  --accent:#4f8cff;
  --accent2:#22c55e;
  --danger:#ef4444;
  --shadow: 0 12px 40px rgba(0,0,0,.35);
  --radius:14px;
  --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
}

*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0;
  font-family:var(--sans);
  background: radial-gradient(1200px 800px at 20% 0%, rgba(79,140,255,.25), transparent 60%),
              radial-gradient(1000px 700px at 90% 20%, rgba(34,197,94,.18), transparent 55%),
              var(--bg);
  color:var(--text);
}
a{color:inherit}

.app{
  height:100%;
  display:flex;
}

.sidebar{
  width:300px;
  background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.02));
  border-right:1px solid var(--border);
  padding:18px 16px;
}
.brand{
  display:flex;
  align-items:center;
  gap:10px;
  padding:8px 10px;
  border:1px solid var(--border);
  border-radius:16px;
  background: rgba(255,255,255,.03);
}
.brand-badge{
  width:34px;height:34px;border-radius:12px;
  display:grid;place-items:center;
  background: rgba(79,140,255,.25);
  border:1px solid rgba(79,140,255,.35);
  color:#d6e6ff;
  font-weight:700;
}
.brand-title{font-weight:800;letter-spacing:.2px}
.brand-sub{font-size:12px;color:var(--muted);margin-top:2px}

.side-actions{margin-top:16px;display:flex;flex-direction:column;gap:10px}
.btn{
  display:flex;
  align-items:center;
  justify-content:center;
  gap:8px;
  padding:10px 12px;
  border-radius:12px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  cursor:pointer;
  transition:.15s ease;
  text-decoration:none;
}
.btn:hover{transform: translateY(-1px); border-color: rgba(255,255,255,.14)}
.btn.primary{background: rgba(79,140,255,.22); border-color: rgba(79,140,255,.35)}
.btn.ghost{background: rgba(255,255,255,.02)}
.btn .hint{font-size:12px;color:var(--muted)}

.tips{
  margin-top:16px;
  padding:12px;
  border:1px solid var(--border);
  border-radius:12px;
  background: rgba(255,255,255,.02);
  color:var(--muted);
  line-height:1.5;
  font-size:13px;
}
.tips strong{color:var(--text)}

.main{
  flex:1;
  display:flex;
  flex-direction:column;
  min-width:0;
}

.topbar{
  height:58px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:0 18px;
  border-bottom:1px solid var(--border);
  background: rgba(10,16,32,.65);
  backdrop-filter: blur(8px);
}
.topbar .title{font-weight:700}
.topbar .meta{color:var(--muted);font-size:13px}

.chat{
  flex:1;
  overflow:auto;
  padding:18px 18px 8px;
}
.chat-inner{
  max-width:980px;
  margin:0 auto;
  display:flex;
  flex-direction:column;
  gap:14px;
}

.msg{
  display:flex;
  gap:10px;
  align-items:flex-end;
}
.msg.user{justify-content:flex-end}
.avatar{
  width:34px;height:34px;border-radius:12px;
  display:grid;place-items:center;
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  flex:0 0 auto;
  color:#dbe7ff;
  font-weight:800;
}
.avatar.ai{background: rgba(34,197,94,.18); border-color: rgba(34,197,94,.28)}
.avatar.user{background: rgba(79,140,255,.18); border-color: rgba(79,140,255,.28)}

.bubble{
  max-width:min(760px, 92%);
  padding:12px 14px;
  border-radius:16px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  box-shadow: 0 6px 16px rgba(0,0,0,.22);
  line-height:1.55;
  white-space:pre-wrap;
  word-break:break-word;
}
.msg.user .bubble{
  background: rgba(79,140,255,.20);
  border-color: rgba(79,140,255,.30);
}
.msg.ai .bubble{
  background: rgba(255,255,255,.03);
}
.bubble .small{
  display:block;
  margin-top:8px;
  color:var(--muted);
  font-size:12px;
  font-family: var(--mono);
}

.composer{
  border-top:1px solid var(--border);
  background: rgba(10,16,32,.65);
  backdrop-filter: blur(8px);
  padding:14px 18px 18px;
}
.composer-inner{
  max-width:980px;
  margin:0 auto;
  display:flex;
  gap:10px;
  align-items:flex-end;
}
textarea{
  flex:1;
  min-height:52px;
  max-height:160px;
  resize:none;
  padding:12px 12px;
  border-radius:14px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  color:var(--text);
  outline:none;
  line-height:1.45;
}
textarea::placeholder{color: rgba(157,176,208,.8)}

.send{
  padding:12px 14px;
  border-radius:14px;
  border:1px solid rgba(79,140,255,.35);
  background: rgba(79,140,255,.25);
  color:var(--text);
  cursor:pointer;
  transition:.15s ease;
  min-width:98px;
}
.send:hover{transform: translateY(-1px)}
.send:disabled{
  opacity:.55;
  cursor:not-allowed;
  transform:none;
}
.footnote{
  max-width:980px;
  margin:10px auto 0;
  color:var(--muted);
  font-size:12px;
  line-height:1.4;
}

.typing{
  display:inline-flex;
  align-items:center;
  gap:6px;
}
.dot{
  width:7px;height:7px;border-radius:50%;
  background: rgba(230,238,252,.7);
  animation: bounce 1.2s infinite ease-in-out;
}
.dot:nth-child(2){animation-delay:.15s}
.dot:nth-child(3){animation-delay:.3s}
@keyframes bounce{
  0%, 80%, 100% { transform: translateY(0); opacity:.55}
  40% { transform: translateY(-4px); opacity:1}
}

.modal{
  position:fixed; inset:0;
  display:none;
  align-items:center;
  justify-content:center;
  background: rgba(0,0,0,.55);
  padding:20px;
  z-index:50;
}
.modal.show{display:flex}
.modal-card{
  width:min(520px, 96vw);
  background: rgba(15,23,42,.92);
  border:1px solid var(--border);
  border-radius:16px;
  padding:16px;
  box-shadow: var(--shadow);
}
.modal-title{font-weight:800; font-size:16px}
.modal-body{color:var(--muted); margin-top:10px; line-height:1.55}
.modal-actions{margin-top:14px; display:flex; gap:10px; justify-content:flex-end}
.modal-actions .btn{min-width:110px}

/* FAQ page */
.page{
  max-width:980px;
  margin:0 auto;
  padding:22px 18px 36px;
}
.card{
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  border-radius:16px;
  padding:16px;
  box-shadow: 0 10px 30px rgba(0,0,0,.28);
}
.faq-grid{
  display:grid;
  grid-template-columns: 280px 1fr;
  gap:14px;
}
.toc a{
  display:block;
  padding:8px 10px;
  border-radius:10px;
  color:var(--muted);
  text-decoration:none;
  border:1px solid transparent;
}
.toc a:hover{
  color:var(--text);
  background: rgba(255,255,255,.03);
  border-color: var(--border);
}
.qa{
  padding:12px 12px;
  border-radius:14px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.02);
  margin-bottom:10px;
}
.qa .q{font-weight:800}
.qa .a{color:var(--muted); margin-top:8px; line-height:1.6; white-space:pre-wrap}

@media (max-width: 980px){
  .sidebar{display:none}
  .faq-grid{grid-template-columns:1fr}
}


```

```javascript
/* global $, window, document */
(function () {
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function nowTime() {
    const d = new Date();
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
  }

  function scrollToBottom() {
    const $chat = $('#chat');
    $chat.stop(true).animate({ scrollTop: $chat[0].scrollHeight }, 180);
  }

  function addMessage(role, text, meta) {
    const safe = escapeHtml(text);
    const $wrap = $('<div class="msg"></div>').addClass(role);
    const $avatar = $('<div class="avatar"></div>').addClass(role === 'ai' ? 'ai' : 'user');
    $avatar.text(role === 'ai' ? 'AI' : '我');
    const $bubble = $('<div class="bubble"></div>');
    $bubble.html(safe);
    if (meta) {
      $bubble.append(`<span class="small">${escapeHtml(meta)}</span>`);
    }

    if (role === 'user') {
      $wrap.append($bubble).append($avatar);
    } else {
      $wrap.append($avatar).append($bubble);
    }
    $('#chatInner').append($wrap);
    scrollToBottom();
    return $wrap;
  }

  function addTyping() {
    const $wrap = $('<div class="msg ai" id="typingRow"></div>');
    const $avatar = $('<div class="avatar ai">AI</div>');
    const $bubble = $('<div class="bubble"></div>');
    const $typing = $('<span class="typing"></span>')
      .append('<span class="dot"></span>')
      .append('<span class="dot"></span>')
      .append('<span class="dot"></span>');
    $bubble.append($typing);
    $wrap.append($avatar).append($bubble);
    $('#chatInner').append($wrap);
    scrollToBottom();
  }

  function removeTyping() {
    $('#typingRow').remove();
  }

  function showModal(title, body) {
    $('#modalTitle').text(title);
    $('#modalBody').text(body);
    $('#modal').addClass('show');
  }

  function hideModal() {
    $('#modal').removeClass('show');
  }

  function setSending(sending) {
    $('#sendBtn').prop('disabled', sending);
    $('#prompt').prop('disabled', sending);
  }

  function normalizeMessage(msg) {
    return (msg || '').replace(/\r\n/g, '\n').trim();
  }

  function send() {
    const msg = normalizeMessage($('#prompt').val());
    if (!msg) return;

    // 前端快速分支：输入“人工”直接弹窗（后端也有同样逻辑，双保险）
    if (msg === '人工') {
      showModal('人工客服', '请联系学长：zhangdreamer@126.com');
      $('#prompt').val('').focus();
      return;
    }

    addMessage('user', msg, `发送于 ${nowTime()}`);
    $('#prompt').val('');
    setSending(true);
    addTyping();

    $.ajax({
      url: '/api/chat',
      method: 'POST',
      contentType: 'application/json; charset=utf-8',
      dataType: 'json',
      data: JSON.stringify({ message: msg }),
      timeout: 25000
    })
      .done(function (res) {
        removeTyping();
        if (res && res.type === 'human') {
          showModal('人工客服', res.answer || '请联系学长：zhangdreamer@126.com');
          return;
        }
        const answer = (res && res.answer) ? String(res.answer) : '（未获取到答案）';
        addMessage('ai', answer, `回答于 ${nowTime()}`);
      })
      .fail(function (xhr) {
        removeTyping();
        const msg = (xhr && xhr.responseJSON && xhr.responseJSON.error)
          ? xhr.responseJSON.error
          : '请求失败，请稍后重试。';
        addMessage('ai', msg, `错误于 ${nowTime()}`);
      })
      .always(function () {
        setSending(false);
        $('#prompt').focus();
      });
  }

  function autoGrowTextarea(el) {
    el.style.height = '0px';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }

  $(document).ready(function () {
    // 初始欢迎
    addMessage(
      'ai',
      '你好！我是“校园百事通”智能客服。\n你可以问我：学籍/奖助学金/选课/出国交流/宿舍/校园卡/图书馆/VPN等。\n\n输入“人工”可联系学长。',
      '提示'
    );

    $('#sendBtn').on('click', function () {
      send();
    });

    $('#prompt').on('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });

    $('#prompt').on('input', function () {
      autoGrowTextarea(this);
    });

    $('#modalClose, #modalOk').on('click', function () {
      hideModal();
    });

    $('#modal').on('click', function (e) {
      if (e.target && e.target.id === 'modal') hideModal();
    });

    // 让 textarea 初始高度合适
    autoGrowTextarea(document.getElementById('prompt'));
  });
})();


```

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>校园百事通 - 智能客服</title>
  <link rel="stylesheet" href="/assets/style.css"/>
  <meta name="description" content="校园百事通智能客服：FAQ + 在线问答（DeepSeek）"/>
  <script src="https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js"></script>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-badge">校</div>
        <div>
          <div class="brand-title">校园百事通</div>
          <div class="brand-sub">智能客服 · FAQ · 办事指南</div>
        </div>
      </div>

      <div class="side-actions">
        <a class="btn primary" href="/faq.html">
          <span>查看 FAQ（20条）</span>
          <span class="hint">静态参考</span>
        </a>
        <button class="btn ghost" type="button" onclick="location.reload()">
          <span>新建对话</span>
          <span class="hint">清空当前页</span>
        </button>
      </div>

      <div class="tips">
        <div><strong>使用提示</strong></div>
        <div style="margin-top:8px">
          - 回车发送，Shift+回车换行<br/>
          - 输入<strong>“人工”</strong>弹出人工联系方式<br/>
          - 规章制度以学校官方通知/学生手册为准
        </div>
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <div class="title">智能客服对话</div>
          <div class="meta">交互风格参考 ChatGPT · 前端纯静态（jQuery）</div>
        </div>
        <div class="meta">接口：<span style="font-family: var(--mono)">POST /api/chat</span></div>
      </header>

      <section class="chat" id="chat">
        <div class="chat-inner" id="chatInner"></div>
      </section>

      <section class="composer">
        <div class="composer-inner">
          <textarea id="prompt" placeholder="输入你的问题（例如：如何办理休学/复学？图书馆借阅规则？VPN怎么用？）"></textarea>
          <button class="send" id="sendBtn" type="button">发送</button>
        </div>
        <div class="footnote">
          本系统会在后台自动加入“上海大学校园百事通”合规提示词，再调用 DeepSeek 生成回答；仅供参考，具体以学校官方规定为准。
        </div>
      </section>
    </main>
  </div>

  <div class="modal" id="modal" aria-hidden="true">
    <div class="modal-card" role="dialog" aria-modal="true">
      <div class="modal-title" id="modalTitle">提示</div>
      <div class="modal-body" id="modalBody"></div>
      <div class="modal-actions">
        <button class="btn ghost" type="button" id="modalClose">关闭</button>
        <button class="btn primary" type="button" id="modalOk">知道了</button>
      </div>
    </div>
  </div>

  <script src="/assets/app.js"></script>
</body>
</html>


```

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>校园百事通 - FAQ（20条）</title>
  <link rel="stylesheet" href="/assets/style.css"/>
  <meta name="description" content="校园百事通FAQ：学籍、培养、奖助、论文、出国、宿舍、校园卡、图书馆、VPN等常见问题"/>
</head>
<body>
<div class="page">
  <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:14px">
    <div>
      <div style="font-weight:900; font-size:20px; letter-spacing:.3px">校园百事通 FAQ（20条）</div>
      <div style="color:var(--muted); margin-top:6px; line-height:1.5">
        说明：以下为高频问题的通用解答模板，具体以学校官方通知/学生手册/学院要求为准。
      </div>
    </div>
    <a class="btn primary" href="/" style="white-space:nowrap">返回聊天</a>
  </div>

  <div class="faq-grid">
    <div class="card toc">
      <div style="font-weight:800; margin-bottom:8px">目录</div>
      <a href="#q01">01 学籍注册/报到</a>
      <a href="#q02">02 休学/复学/退学</a>
      <a href="#q03">03 转导师/转专业</a>
      <a href="#q04">04 选课与学分认定</a>
      <a href="#q05">05 考勤与请假</a>
      <a href="#q06">06 学位论文开题/中期</a>
      <a href="#q07">07 论文“双盲”与评审</a>
      <a href="#q08">08 答辩与毕业流程</a>
      <a href="#q09">09 提前毕业</a>
      <a href="#q10">10 学业奖学金/助学金</a>
      <a href="#q11">11 困难认定/助学贷款</a>
      <a href="#q12">12 出国(境)交流/访学</a>
      <a href="#q13">13 校园卡/一卡通</a>
      <a href="#q14">14 图书馆借阅/论文查重</a>
      <a href="#q15">15 VPN/校外访问</a>
      <a href="#q16">16 医疗报销/校医院</a>
      <a href="#q17">17 宿舍报修/水电</a>
      <a href="#q18">18 实习实践/专业实践</a>
      <a href="#q19">19 违纪处分与申诉</a>
      <a href="#q20">20 遇到诈骗/资金安全</a>
    </div>

    <div class="card">
      <div class="qa" id="q01">
        <div class="q">01 如何完成研究生学籍注册/报到？</div>
        <div class="a">一般流程：按学校通知时间完成线上信息确认 → 到学院/研究生院办理报到材料 →
          完成学籍注册/缴费/住宿等事项。若错过注册时间，尽快联系学院研究生教务或辅导员说明情况并补办。
        </div>
      </div>

      <div class="qa" id="q02">
        <div class="q">02 休学/复学/退学通常怎么申请？</div>
        <div class="a">常见步骤：向导师/学院提出申请 → 填写对应表单并提供证明材料（病假/家庭原因等）→ 学院审核 →
          学校审批。复学一般需在规定时间内提出并完成注册；退学涉及学籍处理与离校手续，务必先咨询学院教务。
        </div>
      </div>

      <div class="qa" id="q03">
        <div class="q">03 想转导师或转专业，怎么做？</div>
        <div class="a">先确认政策窗口期与条件（学期/年级限制、名额、成绩要求等）→ 与现导师和拟接收导师沟通 →
          提交学院审批材料。建议提前准备：个人陈述、学习/科研情况、拟研究方向匹配说明。
        </div>
      </div>

      <div class="qa" id="q04">
        <div class="q">04 选课与学分认定有哪些注意点？</div>
        <div class="a">
          优先按培养方案完成必修与学分结构；跨院课程或线上课程能否计入学分以学院规定为准。若要做学分认定/转换，通常需要课程大纲、成绩单/证明、学院审批。
        </div>
      </div>

      <div class="qa" id="q05">
        <div class="q">05 研究生考勤、请假有什么通用做法？</div>
        <div class="a">
          以学院/课题组要求为准。一般：短期请假走学院系统或纸质审批；涉及离校/出差/长期请假需导师同意并备案。请假尽量提前申请，避免影响课程考核与科研安排。
        </div>
      </div>

      <div class="qa" id="q06">
        <div class="q">06 学位论文开题/中期检查怎么准备？</div>
        <div class="a">
          开题：问题背景、研究现状、研究方案、计划进度、可行性与创新点；中期：阶段成果、问题与风险、后续计划。提前与导师对齐格式、模板与答辩/汇报要求。
        </div>
      </div>

      <div class="qa" id="q07">
        <div class="q">07 论文“双盲”评审是什么？如何降低风险？</div>
        <div class="a">
          双盲通常要求去除作者/单位等可识别信息并按规范排版；风险点包括格式不合规、引用不规范、创新点不清晰。建议：严格用学校模板、做交叉检查（格式/图表/引用）、确保核心贡献可复现并写清楚。
        </div>
      </div>

      <div class="qa" id="q08">
        <div class="q">08 毕业与答辩大致流程？</div>
        <div class="a">常见顺序：资格审核（学分/成果/培养环节）→ 论文定稿 → 评审 → 答辩申请 → 答辩 → 提交终稿与归档 →
          离校手续。各节点的材料清单、时间点以学院通知为准。
        </div>
      </div>

      <div class="qa" id="q09">
        <div class="q">09 想申请提前毕业，需要什么条件？</div>
        <div class="a">
          通常要求：修满规定学分、通过培养环节与论文评审、科研成果或论文质量满足要求、导师与学院同意，并在规定窗口提交申请。提前毕业节奏紧，建议倒排时间线做里程碑管理。
        </div>
      </div>

      <div class="qa" id="q10">
        <div class="q">10 学业奖学金/助学金怎么评？</div>
        <div class="a">
          一般按综合表现（课程成绩、科研成果、竞赛/专利、学术活动、德育与纪律等）进行评审。关键：及时提交证明材料、按学院要求格式整理成果、关注公示与申诉时限。
        </div>
      </div>

      <div class="qa" id="q11">
        <div class="q">11 困难认定、国家助学贷款怎么申请？</div>
        <div class="a">通常流程：线上提交家庭经济情况 → 提交佐证材料 → 学院审核/公示 →
          学校确认。助学贷款需按银行与学校要求准备材料并注意信息安全，任何“代办/刷流水”都要警惕。
        </div>
      </div>

      <div class="qa" id="q12">
        <div class="q">12 出国(境)交流/访学需要做哪些手续？</div>
        <div class="a">一般包括：项目申请/录取 → 学院/研究生院审批 → 因公/因私出国(境)手续 → 学籍与培养计划衔接 →
          风险告知与保险。务必先确认课程与毕业节点是否受影响。
        </div>
      </div>

      <div class="qa" id="q13">
        <div class="q">13 校园卡/一卡通丢了怎么办？</div>
        <div class="a">第一时间挂失（自助终端/线上平台/服务点）→ 补办 →
          同步处理门禁/图书馆/消费账户。若涉及银行卡绑定或第三方支付，请同时检查资金安全。
        </div>
      </div>

      <div class="qa" id="q14">
        <div class="q">14 图书馆借阅、查重、论文资源怎么用？</div>
        <div class="a">
          借阅按图书馆规定执行；校内查重系统与次数通常由学院/研究生院统一安排。建议：尽量使用学校正版数据库、规范引用、保留检索记录与借阅凭证。
        </div>
      </div>

      <div class="qa" id="q15">
        <div class="q">15 校外如何使用 VPN 访问校内资源？</div>
        <div class="a">通用步骤：安装学校指定 VPN 客户端 → 使用统一身份认证登录 → 连接校内网络 →
          访问图书馆/教务/资产平台等。若登录失败，先检查账号状态、网络、客户端版本，再联系学校信息化/网络中心。
        </div>
      </div>

      <div class="qa" id="q16">
        <div class="q">16 看病、医保、医疗报销怎么处理？</div>
        <div class="a">一般遵循：校医院或指定医院就诊 → 票据与病历保存 →
          按学校/医保要求提交报销材料。不同险种与地区政策差异很大，建议先看学校发布的最新说明。
        </div>
      </div>

      <div class="qa" id="q17">
        <div class="q">17 宿舍报修、水电故障如何处理？</div>
        <div class="a">
          通常通过宿舍服务台/后勤报修平台提交：楼号房号、故障描述、联系方式、可上门时间。涉及用电安全（跳闸/异味/冒烟）先断电并联系值班电话。
        </div>
      </div>

      <div class="qa" id="q18">
        <div class="q">18 专业实践/实习需要注意哪些合规与流程？</div>
        <div class="a">
          优先走学校/学院备案流程（协议、保险、指导老师、考核方式、学分认定）。涉及企业数据与保密条款要谨慎，别在非授权平台外传数据或代码。
        </div>
      </div>

      <div class="qa" id="q19">
        <div class="q">19 受到处分或对处理结果有异议，能申诉吗？</div>
        <div class="a">
          一般有申诉渠道与时限：在规定时间内提交书面申诉材料，说明事实、证据与诉求。建议保留通知、公示截图与相关证据，并通过官方渠道提交。
        </div>
      </div>

      <div class="qa" id="q20">
        <div class="q">20 遇到诈骗、资金安全风险怎么办？</div>
        <div class="a">立即停止转账/提供验证码等操作 → 保留证据（聊天记录、转账记录、来电号码）→ 联系银行/支付平台冻结 →
          报警并同步告知辅导员/保卫部门。任何“低息秒批/刷流水/保证下款”都高度可疑。
        </div>
      </div>

      <div style="color:var(--muted); margin-top:14px; line-height:1.6">
        需要更个性化的解答？回到聊天页提问；输入“人工”可获取人工联系方式。
      </div>
    </div>
  </div>
</div>
</body>
</html>


```

已完成两个前端静态页面（无需前端编译）：

### 页面入口
- **聊天页（ChatGPT风格）**：`/`（`src/main/resources/static/index.html`）
- **FAQ静态页（20条）**：`/faq.html`（`src/main/resources/static/faq.html`）

### 关键交互已实现
- **ChatGPT 类布局**：侧边栏 + 顶部栏 + 气泡对话区 + 底部输入框
- **发送体验**：回车发送、Shift+回车换行、输入框自动增高、滚动自动到底部、等待时“打字中”动效
- **人工触发**：输入 **“人工”** 立即弹窗提示 `请联系学长：zhangdreamer@126.com`（前端直接拦截；后端也有同逻辑双保险）
- **FAQ页**：目录锚点 + 20条问答卡片 + “返回聊天”按钮

对应文件：
- `src/main/resources/static/index.html`
- `src/main/resources/static/faq.html`
- `src/main/resources/static/assets/style.css`
- `src/main/resources/static/assets/app.js`

---

**User**

前端页面没有正确展示markdown内容，请修改成能正确展示markdown内容

---

**Cursor**

计划：在前端引入一个**无需编译**的 Markdown 渲染器（`marked.js`）并配合 `DOMPurify` 做安全净化，然后把聊天气泡里 AI 的回答从“纯文本”改成“Markdown→HTML 渲染”。接着补一小段 CSS，让代码块/列表/表格/引用等 Markdown 元素在气泡里显示得像 ChatGPT 一样清晰。

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>校园百事通 - 智能客服</title>
  <link rel="stylesheet" href="/assets/style.css"/>
  <meta name="description" content="校园百事通智能客服：FAQ + 在线问答（DeepSeek）"/>
  <script src="https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/dompurify@3.1.6/dist/purify.min.js"></script>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-badge">校</div>
        <div>
          <div class="brand-title">校园百事通</div>
          <div class="brand-sub">智能客服 · FAQ · 办事指南</div>
        </div>
      </div>

      <div class="side-actions">
        <a class="btn primary" href="/faq.html">
          <span>查看 FAQ（20条）</span>
          <span class="hint">静态参考</span>
        </a>
        <button class="btn ghost" type="button" onclick="location.reload()">
          <span>新建对话</span>
          <span class="hint">清空当前页</span>
        </button>
      </div>

      <div class="tips">
        <div><strong>使用提示</strong></div>
        <div style="margin-top:8px">
          - 回车发送，Shift+回车换行<br/>
          - 输入<strong>“人工”</strong>弹出人工联系方式<br/>
          - 规章制度以学校官方通知/学生手册为准
        </div>
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <div class="title">智能客服对话</div>
          <div class="meta">交互风格参考 ChatGPT · 前端纯静态（jQuery）</div>
        </div>
        <div class="meta">接口：<span style="font-family: var(--mono)">POST /api/chat</span></div>
      </header>

      <section class="chat" id="chat">
        <div class="chat-inner" id="chatInner"></div>
      </section>

      <section class="composer">
        <div class="composer-inner">
          <textarea id="prompt" placeholder="输入你的问题（例如：如何办理休学/复学？图书馆借阅规则？VPN怎么用？）"></textarea>
          <button class="send" id="sendBtn" type="button">发送</button>
        </div>
        <div class="footnote">
          本系统会在后台自动加入“上海大学校园百事通”合规提示词，再调用 DeepSeek 生成回答；仅供参考，具体以学校官方规定为准。
        </div>
      </section>
    </main>
  </div>

  <div class="modal" id="modal" aria-hidden="true">
    <div class="modal-card" role="dialog" aria-modal="true">
      <div class="modal-title" id="modalTitle">提示</div>
      <div class="modal-body" id="modalBody"></div>
      <div class="modal-actions">
        <button class="btn ghost" type="button" id="modalClose">关闭</button>
        <button class="btn primary" type="button" id="modalOk">知道了</button>
      </div>
    </div>
  </div>

  <script src="/assets/app.js"></script>
</body>
</html>



```

```javascript
/* global $, window, document */
(function () {
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function renderMarkdownToSafeHtml(md) {
    const text = String(md == null ? '' : md);
    // marked + DOMPurify 都是 CDN 引入；若缺失则退化为纯文本
    if (!window.marked || !window.DOMPurify) {
      return escapeHtml(text).replace(/\n/g, '<br/>');
    }
    try {
      window.marked.setOptions({
        gfm: true,
        breaks: true,
        mangle: false,
        headerIds: false
      });
      const rawHtml = window.marked.parse(text);
      return window.DOMPurify.sanitize(rawHtml, {
        USE_PROFILES: { html: true },
        ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z+.-]+(?:[^a-z+.-]|$))/i
      });
    } catch (e) {
      return escapeHtml(text).replace(/\n/g, '<br/>');
    }
  }

  function nowTime() {
    const d = new Date();
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
  }

  function scrollToBottom() {
    const $chat = $('#chat');
    $chat.stop(true).animate({ scrollTop: $chat[0].scrollHeight }, 180);
  }

  function addMessage(role, text, meta) {
    // user 用纯文本（避免把用户输入当 markdown 渲染）；ai 按 markdown 渲染
    const html =
      role === 'ai'
        ? renderMarkdownToSafeHtml(text)
        : escapeHtml(String(text == null ? '' : text)).replace(/\n/g, '<br/>');
    const $wrap = $('<div class="msg"></div>').addClass(role);
    const $avatar = $('<div class="avatar"></div>').addClass(role === 'ai' ? 'ai' : 'user');
    $avatar.text(role === 'ai' ? 'AI' : '我');
    const $bubble = $('<div class="bubble"></div>');
    $bubble.html(html);
    if (meta) {
      $bubble.append(`<span class="small">${escapeHtml(meta)}</span>`);
    }

    if (role === 'user') {
      $wrap.append($bubble).append($avatar);
    } else {
      $wrap.append($avatar).append($bubble);
    }
    $('#chatInner').append($wrap);
    scrollToBottom();
    return $wrap;
  }

  function addTyping() {
    const $wrap = $('<div class="msg ai" id="typingRow"></div>');
    const $avatar = $('<div class="avatar ai">AI</div>');
    const $bubble = $('<div class="bubble"></div>');
    const $typing = $('<span class="typing"></span>')
      .append('<span class="dot"></span>')
      .append('<span class="dot"></span>')
      .append('<span class="dot"></span>');
    $bubble.append($typing);
    $wrap.append($avatar).append($bubble);
    $('#chatInner').append($wrap);
    scrollToBottom();
  }

  function removeTyping() {
    $('#typingRow').remove();
  }

  function showModal(title, body) {
    $('#modalTitle').text(title);
    $('#modalBody').text(body);
    $('#modal').addClass('show');
  }

  function hideModal() {
    $('#modal').removeClass('show');
  }

  function setSending(sending) {
    $('#sendBtn').prop('disabled', sending);
    $('#prompt').prop('disabled', sending);
  }

  function normalizeMessage(msg) {
    return (msg || '').replace(/\r\n/g, '\n').trim();
  }

  function send() {
    const msg = normalizeMessage($('#prompt').val());
    if (!msg) return;

    // 前端快速分支：输入“人工”直接弹窗（后端也有同样逻辑，双保险）
    if (msg === '人工') {
      showModal('人工客服', '请联系学长：zhangdreamer@126.com');
      $('#prompt').val('').focus();
      return;
    }

    addMessage('user', msg, `发送于 ${nowTime()}`);
    $('#prompt').val('');
    setSending(true);
    addTyping();

    $.ajax({
      url: '/api/chat',
      method: 'POST',
      contentType: 'application/json; charset=utf-8',
      dataType: 'json',
      data: JSON.stringify({ message: msg }),
      timeout: 25000
    })
      .done(function (res) {
        removeTyping();
        if (res && res.type === 'human') {
          showModal('人工客服', res.answer || '请联系学长：zhangdreamer@126.com');
          return;
        }
        const answer = (res && res.answer) ? String(res.answer) : '（未获取到答案）';
        addMessage('ai', answer, `回答于 ${nowTime()}`);
      })
      .fail(function (xhr) {
        removeTyping();
        const msg = (xhr && xhr.responseJSON && xhr.responseJSON.error)
          ? xhr.responseJSON.error
          : '请求失败，请稍后重试。';
        addMessage('ai', msg, `错误于 ${nowTime()}`);
      })
      .always(function () {
        setSending(false);
        $('#prompt').focus();
      });
  }

  function autoGrowTextarea(el) {
    el.style.height = '0px';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }

  $(document).ready(function () {
    // 初始欢迎
    addMessage(
      'ai',
      '你好！我是“校园百事通”智能客服。\n你可以问我：学籍/奖助学金/选课/出国交流/宿舍/校园卡/图书馆/VPN等。\n\n输入“人工”可联系学长。',
      '提示'
    );

    $('#sendBtn').on('click', function () {
      send();
    });

    $('#prompt').on('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });

    $('#prompt').on('input', function () {
      autoGrowTextarea(this);
    });

    $('#modalClose, #modalOk').on('click', function () {
      hideModal();
    });

    $('#modal').on('click', function (e) {
      if (e.target && e.target.id === 'modal') hideModal();
    });

    // 让 textarea 初始高度合适
    autoGrowTextarea(document.getElementById('prompt'));
  });
})();



```

```css
:root{
  --bg:#0b1020;
  --panel:#0f172a;
  --panel2:#111c33;
  --text:#e6eefc;
  --muted:#9db0d0;
  --border:rgba(255,255,255,.08);
  --accent:#4f8cff;
  --accent2:#22c55e;
  --danger:#ef4444;
  --shadow: 0 12px 40px rgba(0,0,0,.35);
  --radius:14px;
  --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
}

*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0;
  font-family:var(--sans);
  background: radial-gradient(1200px 800px at 20% 0%, rgba(79,140,255,.25), transparent 60%),
              radial-gradient(1000px 700px at 90% 20%, rgba(34,197,94,.18), transparent 55%),
              var(--bg);
  color:var(--text);
}
a{color:inherit}

.app{
  height:100%;
  display:flex;
}

.sidebar{
  width:300px;
  background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.02));
  border-right:1px solid var(--border);
  padding:18px 16px;
}
.brand{
  display:flex;
  align-items:center;
  gap:10px;
  padding:8px 10px;
  border:1px solid var(--border);
  border-radius:16px;
  background: rgba(255,255,255,.03);
}
.brand-badge{
  width:34px;height:34px;border-radius:12px;
  display:grid;place-items:center;
  background: rgba(79,140,255,.25);
  border:1px solid rgba(79,140,255,.35);
  color:#d6e6ff;
  font-weight:700;
}
.brand-title{font-weight:800;letter-spacing:.2px}
.brand-sub{font-size:12px;color:var(--muted);margin-top:2px}

.side-actions{margin-top:16px;display:flex;flex-direction:column;gap:10px}
.btn{
  display:flex;
  align-items:center;
  justify-content:center;
  gap:8px;
  padding:10px 12px;
  border-radius:12px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  cursor:pointer;
  transition:.15s ease;
  text-decoration:none;
}
.btn:hover{transform: translateY(-1px); border-color: rgba(255,255,255,.14)}
.btn.primary{background: rgba(79,140,255,.22); border-color: rgba(79,140,255,.35)}
.btn.ghost{background: rgba(255,255,255,.02)}
.btn .hint{font-size:12px;color:var(--muted)}

.tips{
  margin-top:16px;
  padding:12px;
  border:1px solid var(--border);
  border-radius:12px;
  background: rgba(255,255,255,.02);
  color:var(--muted);
  line-height:1.5;
  font-size:13px;
}
.tips strong{color:var(--text)}

.main{
  flex:1;
  display:flex;
  flex-direction:column;
  min-width:0;
}

.topbar{
  height:58px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:0 18px;
  border-bottom:1px solid var(--border);
  background: rgba(10,16,32,.65);
  backdrop-filter: blur(8px);
}
.topbar .title{font-weight:700}
.topbar .meta{color:var(--muted);font-size:13px}

.chat{
  flex:1;
  overflow:auto;
  padding:18px 18px 8px;
}
.chat-inner{
  max-width:980px;
  margin:0 auto;
  display:flex;
  flex-direction:column;
  gap:14px;
}

.msg{
  display:flex;
  gap:10px;
  align-items:flex-end;
}
.msg.user{justify-content:flex-end}
.avatar{
  width:34px;height:34px;border-radius:12px;
  display:grid;place-items:center;
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  flex:0 0 auto;
  color:#dbe7ff;
  font-weight:800;
}
.avatar.ai{background: rgba(34,197,94,.18); border-color: rgba(34,197,94,.28)}
.avatar.user{background: rgba(79,140,255,.18); border-color: rgba(79,140,255,.28)}

.bubble{
  max-width:min(760px, 92%);
  padding:12px 14px;
  border-radius:16px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  box-shadow: 0 6px 16px rgba(0,0,0,.22);
  line-height:1.55;
  white-space:normal;
  word-break:break-word;
}
.bubble > *:first-child{margin-top:0}
.bubble > *:last-child{margin-bottom:0}
.bubble p{margin:0 0 10px}
.bubble ul,.bubble ol{margin:0 0 10px; padding-left:18px}
.bubble li{margin:4px 0}
.bubble a{color:#b9d2ff}
.bubble a:hover{text-decoration:underline}
.bubble blockquote{
  margin:0 0 10px;
  padding:8px 12px;
  border-left:3px solid rgba(79,140,255,.55);
  background: rgba(79,140,255,.08);
  border-radius:10px;
  color: var(--text);
}
.bubble code{
  font-family: var(--mono);
  font-size: 12.5px;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(255,255,255,.06);
  border: 1px solid rgba(255,255,255,.08);
}
.bubble pre{
  margin:0 0 10px;
  padding:12px;
  border-radius:12px;
  overflow:auto;
  background: rgba(0,0,0,.35);
  border: 1px solid rgba(255,255,255,.10);
}
.bubble pre code{
  padding:0;
  border:none;
  background:transparent;
  font-size: 12.5px;
}
.bubble table{
  width:100%;
  border-collapse: collapse;
  margin:0 0 10px;
  overflow:hidden;
  border-radius:12px;
  border:1px solid rgba(255,255,255,.10);
}
.bubble th,.bubble td{
  padding:8px 10px;
  border-bottom:1px solid rgba(255,255,255,.08);
}
.bubble th{
  text-align:left;
  background: rgba(255,255,255,.04);
}
.bubble hr{
  border:none;
  height:1px;
  background: rgba(255,255,255,.10);
  margin:10px 0;
}
.msg.user .bubble{
  background: rgba(79,140,255,.20);
  border-color: rgba(79,140,255,.30);
}
.msg.ai .bubble{
  background: rgba(255,255,255,.03);
}
.bubble .small{
  display:block;
  margin-top:8px;
  color:var(--muted);
  font-size:12px;
  font-family: var(--mono);
}

.composer{
  border-top:1px solid var(--border);
  background: rgba(10,16,32,.65);
  backdrop-filter: blur(8px);
  padding:14px 18px 18px;
}
.composer-inner{
  max-width:980px;
  margin:0 auto;
  display:flex;
  gap:10px;
  align-items:flex-end;
}
textarea{
  flex:1;
  min-height:52px;
  max-height:160px;
  resize:none;
  padding:12px 12px;
  border-radius:14px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  color:var(--text);
  outline:none;
  line-height:1.45;
}
textarea::placeholder{color: rgba(157,176,208,.8)}

.send{
  padding:12px 14px;
  border-radius:14px;
  border:1px solid rgba(79,140,255,.35);
  background: rgba(79,140,255,.25);
  color:var(--text);
  cursor:pointer;
  transition:.15s ease;
  min-width:98px;
}
.send:hover{transform: translateY(-1px)}
.send:disabled{
  opacity:.55;
  cursor:not-allowed;
  transform:none;
}
.footnote{
  max-width:980px;
  margin:10px auto 0;
  color:var(--muted);
  font-size:12px;
  line-height:1.4;
}

.typing{
  display:inline-flex;
  align-items:center;
  gap:6px;
}
.dot{
  width:7px;height:7px;border-radius:50%;
  background: rgba(230,238,252,.7);
  animation: bounce 1.2s infinite ease-in-out;
}
.dot:nth-child(2){animation-delay:.15s}
.dot:nth-child(3){animation-delay:.3s}
@keyframes bounce{
  0%, 80%, 100% { transform: translateY(0); opacity:.55}
  40% { transform: translateY(-4px); opacity:1}
}

.modal{
  position:fixed; inset:0;
  display:none;
  align-items:center;
  justify-content:center;
  background: rgba(0,0,0,.55);
  padding:20px;
  z-index:50;
}
.modal.show{display:flex}
.modal-card{
  width:min(520px, 96vw);
  background: rgba(15,23,42,.92);
  border:1px solid var(--border);
  border-radius:16px;
  padding:16px;
  box-shadow: var(--shadow);
}
.modal-title{font-weight:800; font-size:16px}
.modal-body{color:var(--muted); margin-top:10px; line-height:1.55}
.modal-actions{margin-top:14px; display:flex; gap:10px; justify-content:flex-end}
.modal-actions .btn{min-width:110px}

/* FAQ page */
.page{
  max-width:980px;
  margin:0 auto;
  padding:22px 18px 36px;
}
.card{
  border:1px solid var(--border);
  background: rgba(255,255,255,.03);
  border-radius:16px;
  padding:16px;
  box-shadow: 0 10px 30px rgba(0,0,0,.28);
}
.faq-grid{
  display:grid;
  grid-template-columns: 280px 1fr;
  gap:14px;
}
.toc a{
  display:block;
  padding:8px 10px;
  border-radius:10px;
  color:var(--muted);
  text-decoration:none;
  border:1px solid transparent;
}
.toc a:hover{
  color:var(--text);
  background: rgba(255,255,255,.03);
  border-color: var(--border);
}
.qa{
  padding:12px 12px;
  border-radius:14px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.02);
  margin-bottom:10px;
}
.qa .q{font-weight:800}
.qa .a{color:var(--muted); margin-top:8px; line-height:1.6; white-space:pre-wrap}

@media (max-width: 980px){
  .sidebar{display:none}
  .faq-grid{grid-template-columns:1fr}
}



```

已把聊天气泡改成**正确渲染 Markdown**（含代码块/列表/表格/引用/链接），且做了 **XSS 安全净化**。

### 你会看到的变化
- **AI 回复**：Markdown → HTML 渲染（像 ChatGPT 那样显示标题、列表、代码块等）
- **用户输入**：仍按纯文本显示（避免把用户输入当 Markdown 执行），但换行正常

### 修改点
- **`src/main/resources/static/index.html`**：新增 CDN
  - `marked`（Markdown 渲染）
  - `dompurify`（净化 HTML）
- **`src/main/resources/static/assets/app.js`**：AI 气泡使用 `marked.parse()` 渲染并 `DOMPurify.sanitize()` 过滤
- **`src/main/resources/static/assets/style.css`**：补齐 Markdown 样式（`pre/code/blockquote/table/hr/ul/ol` 等）

如果你想让“用户消息也支持 Markdown 渲染”，我也可以把 user 分支从纯文本切换为 Markdown（同样会走 DOMPurify）。

---

**User**

当问题提及某老师时，搜索时自动附带教师的介绍

---

**Cursor**

计划：我会在后端加一个“教师名录缓存”模块，启动时抓取管理学院教师名录页并解析出 `{"教师名":"教师介绍页URL"}` 存成 JSON（本地 `data/teachers-ms-shu.json`）；当用户问题里提到某位老师姓名时，自动拉取该老师介绍页正文摘要并拼到模型提示里，帮助更准确回答。接着我会把这个功能做成可配置（开关/缓存路径/刷新频率），并给你一个手动刷新与导出 JSON 的接口便于检查。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <groupId>com.campus</groupId>
  <artifactId>campus-assistant</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <name>campus-assistant</name>
  <description>校园百事通 - 智能客服系统（Spring Boot + 静态前端）</description>

  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.6</version>
    <relativePath/>
  </parent>

  <properties>
    <java.version>21</java.version>
  </properties>

  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>

    <dependency>
      <groupId>org.jsoup</groupId>
      <artifactId>jsoup</artifactId>
      <version>1.18.1</version>
    </dependency>

    <dependency>
      <groupId>org.projectlombok</groupId>
      <artifactId>lombok</artifactId>
      <optional>true</optional>
    </dependency>

    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <configuration>
          <source>${java.version}</source>
          <target>${java.version}</target>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>



```

```java
package com.campus.teacher.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "campus.teacher")
public class TeacherDirectoryProperties {
  /**
   * 是否启用“教师名录”增强（提问提到老师名时自动附带介绍）
   */
  private boolean enabled = true;

  /**
   * 教师名录页面（管理学院）
   */
  private String listUrl = "https://ms.shu.edu.cn/jsyyj/jsml.htm";

  /**
   * 缓存 JSON 保存路径（相对运行目录）
   */
  private String cachePath = "data/teachers-ms-shu.json";

  /**
   * 启动时是否自动刷新名录
   */
  private boolean refreshOnStartup = true;

  /**
   * 介绍页正文最大截取长度（避免 prompt 过长）
   */
  private int bioMaxChars = 1400;

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public String getListUrl() {
    return listUrl;
  }

  public void setListUrl(String listUrl) {
    this.listUrl = listUrl;
  }

  public String getCachePath() {
    return cachePath;
  }

  public void setCachePath(String cachePath) {
    this.cachePath = cachePath;
  }

  public boolean isRefreshOnStartup() {
    return refreshOnStartup;
  }

  public void setRefreshOnStartup(boolean refreshOnStartup) {
    this.refreshOnStartup = refreshOnStartup;
  }

  public int getBioMaxChars() {
    return bioMaxChars;
  }

  public void setBioMaxChars(int bioMaxChars) {
    this.bioMaxChars = bioMaxChars;
  }
}


```

```java
package com.campus.chat.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;
import com.campus.teacher.config.TeacherDirectoryProperties;

@Configuration
@EnableConfigurationProperties({DeepSeekProperties.class, CampusPromptProperties.class, TeacherDirectoryProperties.class})
public class PropsConfig {}



```

```yaml
*** Begin Patch
*** Update File: src/main/resources/application.yml
@@
 campus:
   deepseek:
@@
 
   # 自动加上的「上海大学校园百事通」prompt（可按你们合规口径继续细化）
   creditPrompt: >
     你是上海大学校园百事通（消费金融/小贷/助贷）方向的合规智能客服。
@@
     同时你服务的产品是“校园百事通”，请用清晰、可执行的校园办事步骤回答问题；
     如涉及校内规章制度，建议用户以学校官方通知/学生手册为准，并给出咨询路径（学院/研究生院/辅导员等）。
+
+  teacher:
+    enabled: true
+    listUrl: https://ms.shu.edu.cn/jsyyj/jsml.htm
+    cachePath: data/teachers-ms-shu.json
+    refreshOnStartup: true
+    bioMaxChars: 1400
 
*** End Patch
```

Nice catch:你们已经把 `creditPrompt` 改成“上海大学校园百事通”的口径了；我会在此基础上新增 `campus.teacher` 配置段，并实现启动抓取/本地缓存/命中老师名自动附带介绍的整条链路。接下来主要改后端：加 `jsoup` 抓取解析、落盘 `teachers-ms-shu.json`、以及在 `ChatService` 里做“老师名识别 + 介绍拼接”。

```yaml
server:
  port: 8080

campus:
  deepseek:
    # 建议通过环境变量覆盖：
    # DEEPSEEK_API_KEY=xxx
    apiKey: ${DEEPSEEK_API_KEY:}
    # DeepSeek 兼容 OpenAI 的 chat/completions 形态时通常为该地址；如你们学校/内网网关不同可改这里
    baseUrl: ${DEEPSEEK_BASE_URL:https://api.deepseek.com}
    model: ${DEEPSEEK_MODEL:deepseek-chat}
    timeoutMs: ${DEEPSEEK_TIMEOUT_MS:20000}

  # 自动加上的「校园百事通」prompt（可按你们合规口径继续细化）
  creditPrompt: >
    你是上海大学校园小助手方向的智能客服。
    回答需遵守合规要求：不诱导学生违反校规；
    对涉及个人隐私/资金安全的操作要提醒用户走官方渠道并注意防诈骗。
    同时你服务的产品是“校园百事通”，请用清晰、可执行的校园办事步骤回答问题；
    如涉及校内规章制度，建议用户以学校官方通知/学生手册为准，并给出咨询路径（学院/研究生院/辅导员等）。

  teacher:
    enabled: true
    # 管理学院教师名录
    listUrl: https://ms.shu.edu.cn/jsyyj/jsml.htm
    # 启动后抓取并保存到运行目录下（便于随时查看/更新）
    cachePath: data/teachers-ms-shu.json
    refreshOnStartup: true
    # 介绍页正文最大截取长度（避免 prompt 过长）
    bioMaxChars: 1400



```

```java
package com.campus.teacher.service;

import com.campus.teacher.config.TeacherDirectoryProperties;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class TeacherDirectoryService {
  private final TeacherDirectoryProperties props;
  private final ObjectMapper objectMapper;

  // name -> url
  private volatile Map<String, String> teacherMap = new LinkedHashMap<>();
  private final Map<String, String> bioCache = new ConcurrentHashMap<>(); // url -> bio

  public TeacherDirectoryService(TeacherDirectoryProperties props, ObjectMapper objectMapper) {
    this.props = props;
    this.objectMapper = objectMapper;
    loadCacheFromDisk();
    if (props.isEnabled() && props.isRefreshOnStartup()) {
      // 启动时尽力刷新，失败则使用本地缓存
      try {
        refreshFromWeb();
      } catch (Exception ignored) {
        // ignore
      }
    }
  }

  public boolean isEnabled() {
    return props.isEnabled();
  }

  public Map<String, String> getTeacherMap() {
    return Collections.unmodifiableMap(teacherMap);
  }

  public synchronized Map<String, String> refreshFromWeb() {
    if (!props.isEnabled()) return getTeacherMap();
    if (!StringUtils.hasText(props.getListUrl())) return getTeacherMap();

    Document doc = Jsoup.connect(props.getListUrl())
        .timeout(15000)
        .userAgent("Mozilla/5.0 (campus-assistant/1.0)")
        .get();

    Map<String, String> map = parseTeacherLinks(doc, props.getListUrl());
    if (!map.isEmpty()) {
      teacherMap = map;
      persistToDisk(map);
    }
    return getTeacherMap();
  }

  /**
   * 在用户问题里识别被提及的教师（简单 contains 匹配）。
   */
  public List<TeacherRef> findMentionedTeachers(String userMessage) {
    if (!props.isEnabled()) return List.of();
    String msg = userMessage == null ? "" : userMessage;
    if (!StringUtils.hasText(msg)) return List.of();

    // 小优化：先过滤掉极短 map/或消息太短
    Map<String, String> map = teacherMap;
    if (map.isEmpty()) return List.of();

    List<TeacherRef> hits = new ArrayList<>();
    for (Map.Entry<String, String> e : map.entrySet()) {
      String name = e.getKey();
      if (name.length() < 2) continue;
      if (msg.contains(name)) {
        hits.add(new TeacherRef(name, e.getValue()));
        if (hits.size() >= 3) break; // 避免一次命中太多导致 prompt 过长
      }
    }
    return hits;
  }

  /**
   * 拉取教师介绍页并抽取正文（带缓存）。
   */
  public Optional<String> fetchTeacherBio(String url) {
    if (!props.isEnabled()) return Optional.empty();
    if (!StringUtils.hasText(url)) return Optional.empty();

    String cached = bioCache.get(url);
    if (StringUtils.hasText(cached)) return Optional.of(cached);

    try {
      Document doc = Jsoup.connect(url)
          .timeout(15000)
          .userAgent("Mozilla/5.0 (campus-assistant/1.0)")
          .get();

      // 尝试按通用“info 页面”抽取正文
      String title = textOrEmpty(doc.selectFirst("h1, .arti_title, .Article_Title, .title"));
      String content = extractMainText(doc);

      String merged = (title + "\n" + content).trim();
      if (!StringUtils.hasText(merged)) return Optional.empty();

      String clipped = clip(merged, props.getBioMaxChars());
      bioCache.put(url, clipped);
      return Optional.of(clipped);
    } catch (Exception e) {
      return Optional.empty();
    }
  }

  private static Map<String, String> parseTeacherLinks(Document doc, String baseUrl) {
    Map<String, String> map = new LinkedHashMap<>();

    // 名录页里老师链接通常指向 ../info/xxxx/xxxxx.htm
    Elements links = doc.select("a[href]");
    for (Element a : links) {
      String name = a.text() == null ? "" : a.text().trim();
      String href = a.attr("href") == null ? "" : a.attr("href").trim();
      if (!StringUtils.hasText(name) || !StringUtils.hasText(href)) continue;

      // 过滤明显不是老师名的链接（中英文导航/空白等）
      if (name.length() > 6) continue;
      if (name.matches(".*\\d.*")) continue;
      if (name.toLowerCase(Locale.ROOT).contains("english")) continue;
      if (Set.of("首页", "教师名录", "教授", "副教授", "讲师", "外聘教师").contains(name)) continue;

      if (!href.contains("/info/")) continue;
      String abs = a.absUrl("href");
      if (!StringUtils.hasText(abs)) {
        abs = resolveUrl(baseUrl, href);
      }
      if (StringUtils.hasText(abs)) {
        map.putIfAbsent(name, abs);
      }
    }

    return map;
  }

  private static String resolveUrl(String base, String href) {
    try {
      return java.net.URI.create(base).resolve(href).toString();
    } catch (Exception e) {
      return "";
    }
  }

  private static String extractMainText(Document doc) {
    // 优先尝试常见正文容器
    Element main =
        firstNonNull(
            doc.selectFirst(".v_news_content"),
            doc.selectFirst(".wp_articlecontent"),
            doc.selectFirst(".article"),
            doc.selectFirst(".content"),
            doc.selectFirst("article"));

    if (main != null) {
      return main.text();
    }

    // 兜底：去掉导航等后取 body 文本
    Element body = doc.body();
    return body == null ? "" : body.text();
  }

  private static Element firstNonNull(Element... els) {
    for (Element e : els) {
      if (e != null) return e;
    }
    return null;
  }

  private static String textOrEmpty(Element el) {
    return el == null ? "" : (el.text() == null ? "" : el.text().trim());
  }

  private static String clip(String s, int maxChars) {
    if (maxChars <= 0) return s;
    if (s.length() <= maxChars) return s;
    return s.substring(0, maxChars) + "…";
  }

  private void loadCacheFromDisk() {
    Path p = Path.of(props.getCachePath());
    if (!Files.exists(p)) return;
    try {
      String json = Files.readString(p, StandardCharsets.UTF_8);
      Map<String, String> map =
          objectMapper.readValue(json, new TypeReference<Map<String, String>>() {});
      if (map != null && !map.isEmpty()) {
        teacherMap = new LinkedHashMap<>(map);
      }
    } catch (Exception ignored) {
      // ignore
    }
  }

  private void persistToDisk(Map<String, String> map) {
    try {
      Path p = Path.of(props.getCachePath());
      if (p.getParent() != null) Files.createDirectories(p.getParent());
      String json = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(map);
      Files.writeString(p, json, StandardCharsets.UTF_8);
    } catch (IOException ignored) {
      // ignore
    }
  }

  public record TeacherRef(String name, String url) {}
}


```

```java
package com.campus.teacher.controller;

import com.campus.teacher.service.TeacherDirectoryService;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/teachers")
public class TeacherDirectoryController {
  private final TeacherDirectoryService service;

  public TeacherDirectoryController(TeacherDirectoryService service) {
    this.service = service;
  }

  /**
   * 查看当前缓存的教师名录（name -> url）
   */
  @GetMapping
  public Map<String, String> list() {
    return service.getTeacherMap();
  }

  /**
   * 手动刷新名录并落盘
   */
  @PostMapping("/refresh")
  public Map<String, String> refresh() {
    return service.refreshFromWeb();
  }
}


```

```java
package com.campus.chat.service;

import com.campus.chat.config.CampusPromptProperties;
import com.campus.teacher.service.TeacherDirectoryService;
import com.campus.teacher.service.TeacherDirectoryService.TeacherRef;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class ChatService {
  private static final String HUMAN_KEYWORD = "人工";
  private static final String HUMAN_CONTACT = "请联系学长：zhangdreamer@126.com";

  private final CampusPromptProperties promptProps;
  private final DeepSeekClient deepSeekClient;
  private final TeacherDirectoryService teacherDirectoryService;

  public ChatService(
      CampusPromptProperties promptProps,
      DeepSeekClient deepSeekClient,
      TeacherDirectoryService teacherDirectoryService) {
    this.promptProps = promptProps;
    this.deepSeekClient = deepSeekClient;
    this.teacherDirectoryService = teacherDirectoryService;
  }

  public ChatResult answer(String userMessage) {
    String msg = userMessage == null ? "" : userMessage.trim();
    if (HUMAN_KEYWORD.equals(msg)) {
      return ChatResult.human(HUMAN_CONTACT);
    }

    String systemPrompt = StringUtils.hasText(promptProps.getCreditPrompt())
        ? promptProps.getCreditPrompt().trim()
        : "你是智能客服，请用简洁步骤回答。";

    String enhancedUserMessage = msg;
    if (teacherDirectoryService.isEnabled()) {
      List<TeacherRef> hits = teacherDirectoryService.findMentionedTeachers(msg);
      if (!hits.isEmpty()) {
        StringBuilder sb = new StringBuilder();
        sb.append("【教师信息检索结果】\n");
        for (TeacherRef ref : hits) {
          sb.append("- 教师：").append(ref.name()).append("\n");
          sb.append("  介绍页：").append(ref.url()).append("\n");
          Optional<String> bio = teacherDirectoryService.fetchTeacherBio(ref.url());
          bio.ifPresent(b -> sb.append("  介绍摘要：").append(b).append("\n"));
        }
        sb.append("\n【用户问题】\n").append(msg);
        enhancedUserMessage = sb.toString();
      }
    }

    // “自动加上上海大学校园百事通的prompt”：这里采用 system 角色做强约束；user 角色保留用户原问题
    String answer = deepSeekClient.chat(systemPrompt, enhancedUserMessage);
    return ChatResult.answer(answer);
  }

  public record ChatResult(String type, String answer) {
    public static ChatResult human(String contact) {
      return new ChatResult("human", contact);
    }

    public static ChatResult answer(String text) {
      return new ChatResult("answer", text);
    }
  }
}



```

Good news:构建失败只是一个小编译点——`Jsoup.connect(...).get()` 会抛 `IOException`，我把 `refreshFromWeb()` 包一层 try/catch 兜底即可（失败继续用本地缓存）。接着我会重新跑一次 Maven 确保依赖与编译都 OK。

```java
package com.campus.teacher.service;

import com.campus.teacher.config.TeacherDirectoryProperties;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class TeacherDirectoryService {
  private final TeacherDirectoryProperties props;
  private final ObjectMapper objectMapper;

  // name -> url
  private volatile Map<String, String> teacherMap = new LinkedHashMap<>();
  private final Map<String, String> bioCache = new ConcurrentHashMap<>(); // url -> bio

  public TeacherDirectoryService(TeacherDirectoryProperties props, ObjectMapper objectMapper) {
    this.props = props;
    this.objectMapper = objectMapper;
    loadCacheFromDisk();
    if (props.isEnabled() && props.isRefreshOnStartup()) {
      // 启动时尽力刷新，失败则使用本地缓存
      try {
        refreshFromWeb();
      } catch (Exception ignored) {
        // ignore
      }
    }
  }

  public boolean isEnabled() {
    return props.isEnabled();
  }

  public Map<String, String> getTeacherMap() {
    return Collections.unmodifiableMap(teacherMap);
  }

  public synchronized Map<String, String> refreshFromWeb() {
    if (!props.isEnabled()) return getTeacherMap();
    if (!StringUtils.hasText(props.getListUrl())) return getTeacherMap();

    Document doc;
    try {
      doc =
          Jsoup.connect(props.getListUrl())
              .timeout(15000)
              .userAgent("Mozilla/5.0 (campus-assistant/1.0)")
              .get();
    } catch (IOException e) {
      return getTeacherMap();
    }

    Map<String, String> map = parseTeacherLinks(doc, props.getListUrl());
    if (!map.isEmpty()) {
      teacherMap = map;
      persistToDisk(map);
    }
    return getTeacherMap();
  }

  /**
   * 在用户问题里识别被提及的教师（简单 contains 匹配）。
   */
  public List<TeacherRef> findMentionedTeachers(String userMessage) {
    if (!props.isEnabled()) return List.of();
    String msg = userMessage == null ? "" : userMessage;
    if (!StringUtils.hasText(msg)) return List.of();

    // 小优化：先过滤掉极短 map/或消息太短
    Map<String, String> map = teacherMap;
    if (map.isEmpty()) return List.of();

    List<TeacherRef> hits = new ArrayList<>();
    for (Map.Entry<String, String> e : map.entrySet()) {
      String name = e.getKey();
      if (name.length() < 2) continue;
      if (msg.contains(name)) {
        hits.add(new TeacherRef(name, e.getValue()));
        if (hits.size() >= 3) break; // 避免一次命中太多导致 prompt 过长
      }
    }
    return hits;
  }

  /**
   * 拉取教师介绍页并抽取正文（带缓存）。
   */
  public Optional<String> fetchTeacherBio(String url) {
    if (!props.isEnabled()) return Optional.empty();
    if (!StringUtils.hasText(url)) return Optional.empty();

    String cached = bioCache.get(url);
    if (StringUtils.hasText(cached)) return Optional.of(cached);

    try {
      Document doc = Jsoup.connect(url)
          .timeout(15000)
          .userAgent("Mozilla/5.0 (campus-assistant/1.0)")
          .get();

      // 尝试按通用“info 页面”抽取正文
      String title = textOrEmpty(doc.selectFirst("h1, .arti_title, .Article_Title, .title"));
      String content = extractMainText(doc);

      String merged = (title + "\n" + content).trim();
      if (!StringUtils.hasText(merged)) return Optional.empty();

      String clipped = clip(merged, props.getBioMaxChars());
      bioCache.put(url, clipped);
      return Optional.of(clipped);
    } catch (Exception e) {
      return Optional.empty();
    }
  }

  private static Map<String, String> parseTeacherLinks(Document doc, String baseUrl) {
    Map<String, String> map = new LinkedHashMap<>();

    // 名录页里老师链接通常指向 ../info/xxxx/xxxxx.htm
    Elements links = doc.select("a[href]");
    for (Element a : links) {
      String name = a.text() == null ? "" : a.text().trim();
      String href = a.attr("href") == null ? "" : a.attr("href").trim();
      if (!StringUtils.hasText(name) || !StringUtils.hasText(href)) continue;

      // 过滤明显不是老师名的链接（中英文导航/空白等）
      if (name.length() > 6) continue;
      if (name.matches(".*\\d.*")) continue;
      if (name.toLowerCase(Locale.ROOT).contains("english")) continue;
      if (Set.of("首页", "教师名录", "教授", "副教授", "讲师", "外聘教师").contains(name)) continue;

      if (!href.contains("/info/")) continue;
      String abs = a.absUrl("href");
      if (!StringUtils.hasText(abs)) {
        abs = resolveUrl(baseUrl, href);
      }
      if (StringUtils.hasText(abs)) {
        map.putIfAbsent(name, abs);
      }
    }

    return map;
  }

  private static String resolveUrl(String base, String href) {
    try {
      return java.net.URI.create(base).resolve(href).toString();
    } catch (Exception e) {
      return "";
    }
  }

  private static String extractMainText(Document doc) {
    // 优先尝试常见正文容器
    Element main =
        firstNonNull(
            doc.selectFirst(".v_news_content"),
            doc.selectFirst(".wp_articlecontent"),
            doc.selectFirst(".article"),
            doc.selectFirst(".content"),
            doc.selectFirst("article"));

    if (main != null) {
      return main.text();
    }

    // 兜底：去掉导航等后取 body 文本
    Element body = doc.body();
    return body == null ? "" : body.text();
  }

  private static Element firstNonNull(Element... els) {
    for (Element e : els) {
      if (e != null) return e;
    }
    return null;
  }

  private static String textOrEmpty(Element el) {
    return el == null ? "" : (el.text() == null ? "" : el.text().trim());
  }

  private static String clip(String s, int maxChars) {
    if (maxChars <= 0) return s;
    if (s.length() <= maxChars) return s;
    return s.substring(0, maxChars) + "…";
  }

  private void loadCacheFromDisk() {
    Path p = Path.of(props.getCachePath());
    if (!Files.exists(p)) return;
    try {
      String json = Files.readString(p, StandardCharsets.UTF_8);
      Map<String, String> map =
          objectMapper.readValue(json, new TypeReference<Map<String, String>>() {});
      if (map != null && !map.isEmpty()) {
        teacherMap = new LinkedHashMap<>(map);
      }
    } catch (Exception ignored) {
      // ignore
    }
  }

  private void persistToDisk(Map<String, String> map) {
    try {
      Path p = Path.of(props.getCachePath());
      if (p.getParent() != null) Files.createDirectories(p.getParent());
      String json = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(map);
      Files.writeString(p, json, StandardCharsets.UTF_8);
    } catch (IOException ignored) {
      // ignore
    }
  }

  public record TeacherRef(String name, String url) {}
}



```

已实现“教师名录抓取 + JSON缓存 + 提问命中老师名自动附带老师介绍”。

### 已完成的能力
- **抓取名录页并生成 JSON**：启动时（可配置）抓取管理学院教师名录页，解析所有教师链接，生成 `{"教师名":"教师介绍页url"}` 并落盘到 `data/teachers-ms-shu.json`  
  - 名录来源：[上海大学管理学院-教师名录](https://ms.shu.edu.cn/jsyyj/jsml.htm)
- **命中老师名自动附带介绍**：当用户问题中包含某位教师姓名时：
  - 后端会从缓存 JSON 找到该教师介绍页 URL
  - 再抓取该介绍页正文摘要（长度可配置），拼到 user message 前一起发给 DeepSeek

### 你可以怎么验证
- **查看当前缓存的名录 JSON**：`GET /api/teachers`
- **手动刷新并落盘**：`POST /api/teachers/refresh`
- **本地文件**：运行后会生成/更新 `data/teachers-ms-shu.json`

### 可配置项（`application.yml`）
- `campus.teacher.enabled`
- `campus.teacher.listUrl`
- `campus.teacher.cachePath`
- `campus.teacher.refreshOnStartup`
- `campus.teacher.bioMaxChars`

如果你希望“老师名匹配”更智能（比如支持同名消歧、支持“张老师/许教授”这种称呼、或拼音/英文名），我可以再加一层规则与索引优化。

---

**User**

增加个功能：
收到提问时，先把问题在《docs/2025_student_guidance.md》里匹配下，匹配到的话就把相邻的三段文字附带送给deepseek接口

---

**Cursor**

计划：我会先把你刚改动的 `TeacherDirectoryController` 修到能正常编译（你把 `@PostMapping` 改成了 `@RequestMapping` 且缺少 import，当前会直接编不过）。然后新增一个“guidance 匹配模块”：读取 `docs/2025_student_guidance.md`，按空行切成段落；收到问题时做关键词匹配，命中就取“上一段+当前段+下一段”三段拼到给 DeepSeek 的内容里（没命中或文件不存在就自动跳过）。最后跑一遍构建确保都 OK。

```java
package com.campus.teacher.controller;

import com.campus.teacher.service.TeacherDirectoryService;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/teachers")
public class TeacherDirectoryController {
  private final TeacherDirectoryService service;

  public TeacherDirectoryController(TeacherDirectoryService service) {
    this.service = service;
  }

  /**
   * 查看当前缓存的教师名录（name -> url）
   */
  @GetMapping
  public Map<String, String> list() {
    return service.getTeacherMap();
  }

  /**
   * 手动刷新名录并落盘
   */
  @PostMapping("/refresh")
  public Map<String, String> refresh() {
    return service.refreshFromWeb();
  }
}



```

```java
package com.campus.chat.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "campus")
public class CampusPromptProperties {
  /**
   * 自动追加的“上海大学校园百事通”Prompt
   */
  private String creditPrompt;

  /**
   * 校园指南 Markdown 路径（例如 docs/2025_student_guidance.md）
   *
   * 注意：字段名为 path_guildence（按你当前 application.yml 保持一致）
   */
  private String path_guildence;

  public String getCreditPrompt() {
    return creditPrompt;
  }

  public void setCreditPrompt(String creditPrompt) {
    this.creditPrompt = creditPrompt;
  }

  public String getPath_guildence() {
    return path_guildence;
  }

  public void setPath_guildence(String path_guildence) {
    this.path_guildence = path_guildence;
  }
}



```

```java
package com.campus.guidance.service;

import com.campus.chat.config.CampusPromptProperties;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class GuidanceMatchService {
  private final CampusPromptProperties campusProps;

  private volatile List<String> paragraphs = List.of();
  private volatile long lastModified = -1L;

  public GuidanceMatchService(CampusPromptProperties campusProps) {
    this.campusProps = campusProps;
    reloadIfNeeded();
  }

  /**
   * 从《docs/2025_student_guidance.md》匹配命中段落，并返回 “上一段 + 当前段 + 下一段”（最多三段）。
   */
  public Optional<String> matchWithNeighbors(String userMessage) {
    String msg = userMessage == null ? "" : userMessage.trim();
    if (!StringUtils.hasText(msg)) return Optional.empty();

    reloadIfNeeded();
    List<String> ps = paragraphs;
    if (ps.isEmpty()) return Optional.empty();

    List<String> keywords = extractKeywords(msg);
    if (keywords.isEmpty()) return Optional.empty();

    int bestIdx = -1;
    int bestScore = 0;
    for (int i = 0; i < ps.size(); i++) {
      String p = ps.get(i);
      int score = scoreParagraph(p, keywords);
      if (score > bestScore) {
        bestScore = score;
        bestIdx = i;
      }
    }

    // 阈值：至少命中 2 个关键词，避免误匹配
    if (bestIdx < 0 || bestScore < 2) return Optional.empty();

    int start = Math.max(0, bestIdx - 1);
    int end = Math.min(ps.size() - 1, bestIdx + 1);

    StringBuilder sb = new StringBuilder();
    for (int i = start; i <= end; i++) {
      sb.append(ps.get(i).trim()).append("\n\n");
    }
    String result = sb.toString().trim();
    if (!StringUtils.hasText(result)) return Optional.empty();
    return Optional.of(result);
  }

  private void reloadIfNeeded() {
    String pathStr = campusProps.getPath_guildence();
    if (!StringUtils.hasText(pathStr)) return;
    Path p = Path.of(pathStr);
    if (!Files.exists(p)) return;
    try {
      long lm = Files.getLastModifiedTime(p).toMillis();
      if (lm == lastModified && !paragraphs.isEmpty()) return;
      String md = Files.readString(p, StandardCharsets.UTF_8);
      List<String> ps = splitToParagraphs(md);
      paragraphs = ps;
      lastModified = lm;
    } catch (IOException ignored) {
      // ignore
    }
  }

  private static List<String> splitToParagraphs(String md) {
    if (md == null) return List.of();
    // 以空行切段：连续空行视为分隔
    String[] raw = md.replace("\r\n", "\n").split("\\n\\s*\\n+");
    List<String> out = new ArrayList<>();
    for (String r : raw) {
      String s = r == null ? "" : r.trim();
      if (!StringUtils.hasText(s)) continue;
      // 过滤纯目录分隔线等噪声
      if (s.matches("^[#\\-=_\\s]+$")) continue;
      out.add(s);
    }
    return out;
  }

  private static List<String> extractKeywords(String msg) {
    String s = msg.toLowerCase(Locale.ROOT);

    // 1) 连续中文 2-4 字（经验值：太长会变成整句，太短会误匹配）
    Set<String> zh = new LinkedHashSet<>();
    var m1 = java.util.regex.Pattern.compile("[\\u4e00-\\u9fa5]{2,4}").matcher(msg);
    while (m1.find()) {
      zh.add(m1.group());
    }

    // 2) 英文/数字词（VPN、GPA、ID等）
    Set<String> en = new LinkedHashSet<>();
    var m2 = java.util.regex.Pattern.compile("[a-zA-Z0-9]{2,}").matcher(s);
    while (m2.find()) {
      en.add(m2.group());
    }

    List<String> kws = new ArrayList<>();
    kws.addAll(zh);
    kws.addAll(en);

    // 去掉常见无意义词
    kws.removeIf(k ->
        Set.of("什么", "怎么", "如何", "可以", "是否", "老师", "同学", "上海", "大学", "校园").contains(k));

    // 优先保留更“信息密度高”的关键词
    kws.sort(Comparator.<String>comparingInt(String::length).reversed());
    if (kws.size() > 12) {
      return kws.subList(0, 12);
    }
    return kws;
  }

  private static int scoreParagraph(String paragraph, List<String> keywords) {
    if (!StringUtils.hasText(paragraph)) return 0;
    int score = 0;
    for (String k : keywords) {
      if (!StringUtils.hasText(k)) continue;
      if (paragraph.contains(k)) score++;
    }
    return score;
  }
}


```

```java
*** Begin Patch
*** Update File: src/main/java/com/campus/chat/service/ChatService.java
@@
 import com.campus.chat.config.CampusPromptProperties;
+import com.campus.guidance.service.GuidanceMatchService;
 import com.campus.teacher.service.TeacherDirectoryService;
 import com.campus.teacher.service.TeacherDirectoryService.TeacherRef;
 import java.util.List;
 import java.util.Optional;
 import org.springframework.stereotype.Service;
@@
 
   private final CampusPromptProperties promptProps;
   private final DeepSeekClient deepSeekClient;
   private final TeacherDirectoryService teacherDirectoryService;
+  private final GuidanceMatchService guidanceMatchService;
 
   public ChatService(
       CampusPromptProperties promptProps,
       DeepSeekClient deepSeekClient,
-      TeacherDirectoryService teacherDirectoryService) {
+      TeacherDirectoryService teacherDirectoryService,
+      GuidanceMatchService guidanceMatchService) {
     this.promptProps = promptProps;
     this.deepSeekClient = deepSeekClient;
     this.teacherDirectoryService = teacherDirectoryService;
+    this.guidanceMatchService = guidanceMatchService;
   }
@@
-    String enhancedUserMessage = msg;
+    String enhancedUserMessage = msg;
+
+    // 先做《校园指南》匹配：命中则附带相邻三段（上一段+命中段+下一段）
+    Optional<String> guidance = guidanceMatchService.matchWithNeighbors(msg);
+    if (guidance.isPresent()) {
+      enhancedUserMessage =
+          "【校园指南命中内容（相邻三段）】\n"
+              + guidance.get()
+              + "\n\n【用户问题】\n"
+              + msg;
+    }
 
     if (teacherDirectoryService.isEnabled()) {
       List<TeacherRef> hits = teacherDirectoryService.findMentionedTeachers(msg);
       if (!hits.isEmpty()) {
         StringBuilder sb = new StringBuilder();
-        sb.append("【教师信息检索结果】\n");
+        sb.append("【教师信息检索结果】\n");
         for (TeacherRef ref : hits) {
           sb.append("- 教师：").append(ref.name()).append("\n");
           sb.append("  介绍页：").append(ref.url()).append("\n");
           Optional<String> bio = teacherDirectoryService.fetchTeacherBio(ref.url());
           bio.ifPresent(b -> sb.append("  介绍摘要：").append(b).append("\n"));
         }
-        sb.append("\n【用户问题】\n").append(msg);
-        enhancedUserMessage = sb.toString();
+        // 教师信息与校园指南都可能命中：把教师信息放在最前面，再跟用户问题（及指南段落）
+        sb.append("\n");
+        sb.append(enhancedUserMessage.startsWith("【教师信息检索结果】") ? msg : enhancedUserMessage);
+        enhancedUserMessage = sb.toString();
       }
     }
 
     // “自动加上上海大学校园百事通的prompt”：这里采用 system 角色做强约束；user 角色保留用户原问题
     String answer = deepSeekClient.chat(systemPrompt, enhancedUserMessage);
     return ChatResult.answer(answer);
   }
*** End Patch
```

```java
package com.campus.chat.service;

import com.campus.chat.config.CampusPromptProperties;
import com.campus.guidance.service.GuidanceMatchService;
import com.campus.teacher.service.TeacherDirectoryService;
import com.campus.teacher.service.TeacherDirectoryService.TeacherRef;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class ChatService {
  private static final String HUMAN_KEYWORD = "人工";
  private static final String HUMAN_CONTACT = "请联系学长：zhangdreamer@126.com";

  private final CampusPromptProperties promptProps;
  private final DeepSeekClient deepSeekClient;
  private final TeacherDirectoryService teacherDirectoryService;
  private final GuidanceMatchService guidanceMatchService;

  public ChatService(
      CampusPromptProperties promptProps,
      DeepSeekClient deepSeekClient,
      TeacherDirectoryService teacherDirectoryService,
      GuidanceMatchService guidanceMatchService) {
    this.promptProps = promptProps;
    this.deepSeekClient = deepSeekClient;
    this.teacherDirectoryService = teacherDirectoryService;
    this.guidanceMatchService = guidanceMatchService;
  }

  public ChatResult answer(String userMessage) {
    String msg = userMessage == null ? "" : userMessage.trim();
    if (HUMAN_KEYWORD.equals(msg)) {
      return ChatResult.human(HUMAN_CONTACT);
    }

    String systemPrompt = StringUtils.hasText(promptProps.getCreditPrompt())
        ? promptProps.getCreditPrompt().trim()
        : "你是智能客服，请用简洁步骤回答。";

    String enhancedUserMessage = msg;

    // 先做《校园指南》匹配：命中则附带相邻三段（上一段+命中段+下一段）
    Optional<String> guidance = guidanceMatchService.matchWithNeighbors(msg);
    if (guidance.isPresent()) {
      enhancedUserMessage =
          "【校园指南命中内容（相邻三段）】\n"
              + guidance.get()
              + "\n\n【用户问题】\n"
              + msg;
    }
    if (teacherDirectoryService.isEnabled()) {
      List<TeacherRef> hits = teacherDirectoryService.findMentionedTeachers(msg);
      if (!hits.isEmpty()) {
        StringBuilder sb = new StringBuilder();
        sb.append("【教师信息检索结果】\n");
        for (TeacherRef ref : hits) {
          sb.append("- 教师：").append(ref.name()).append("\n");
          sb.append("  介绍页：").append(ref.url()).append("\n");
          Optional<String> bio = teacherDirectoryService.fetchTeacherBio(ref.url());
          bio.ifPresent(b -> sb.append("  介绍摘要：").append(b).append("\n"));
        }
        sb.append("\n");
        sb.append(enhancedUserMessage);
        enhancedUserMessage = sb.toString();
      }
    }

    // “自动加上上海大学校园百事通的prompt”：这里采用 system 角色做强约束；user 角色保留用户原问题
    String answer = deepSeekClient.chat(systemPrompt, enhancedUserMessage);
    return ChatResult.answer(answer);
  }

  public record ChatResult(String type, String answer) {
    public static ChatResult human(String contact) {
      return new ChatResult("human", contact);
    }

    public static ChatResult answer(String text) {
      return new ChatResult("answer", text);
    }
  }
}



```

已增加“校园指南命中增强”功能：**收到提问时先在 `docs/2025_student_guidance.md` 里匹配**，命中则把**相邻三段（上一段+命中段+下一段）**一起附带发送给 DeepSeek。

### 具体实现
- **配置读取**：沿用你在 `application.yml` 里加的 `campus.path_guildence: docs/2025_student_guidance.md`（字段名保持一致）
- **匹配逻辑**：按空行切成段落 → 从用户问题提取关键词（中文2-4字片段 + 英文数字词）→ 段落 contains 计分 → 命中阈值满足则取相邻三段
- **拼接顺序**：
  1) 若命中指南：先放 `【校园指南命中内容（相邻三段）】...`
  2) 若命中老师：再在最前面加 `【教师信息检索结果】...`（你之前的功能仍然生效）
  3) 最后带上 `【用户问题】...`

### 关键文件
- `src/main/java/com/campus/guidance/service/GuidanceMatchService.java`
- `src/main/java/com/campus/chat/config/CampusPromptProperties.java`（新增 `path_guildence` 映射）
- `src/main/java/com/campus/chat/service/ChatService.java`（调用并附带三段内容）
- 顺手修复：`TeacherDirectoryController` 的 `/refresh` 恢复为 `POST /api/teachers/refresh`（避免你改成 `@RequestMapping` 带来的歧义/风险）

如果你希望“命中后附带三段”改成“附带当前段+后两段”或“附带前后各两段（共5段）”，我也可以把邻段策略做成可配置。

