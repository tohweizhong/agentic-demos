package main

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"golang.org/x/oauth2"
)

// fakeUpstream records the requests that the server sends to the Google APIs.
type fakeUpstream struct {
	t        *testing.T
	requests []*http.Request
	bodies   []string
	handler  func(w http.ResponseWriter, r *http.Request)
}

func (f *fakeUpstream) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	body, _ := io.ReadAll(r.Body)
	f.requests = append(f.requests, r)
	f.bodies = append(f.bodies, string(body))
	f.handler(w, r)
}

func newTestServer(t *testing.T, handler func(w http.ResponseWriter, r *http.Request)) (*httptest.Server, *fakeUpstream) {
	t.Helper()
	up := &fakeUpstream{t: t, handler: handler}
	upstream := httptest.NewServer(up)
	t.Cleanup(upstream.Close)
	cfg := Config{
		Project:     "test-project",
		Bucket:      "test-bucket",
		AgentsBase:  upstream.URL + "/agents-api",
		StorageBase: upstream.URL + "/storage",
		StaticDir:   t.TempDir(),
	}
	tokens := oauth2.StaticTokenSource(&oauth2.Token{AccessToken: "secret-token"})
	srv := httptest.NewServer(NewServer(cfg, tokens, upstream.Client()).Routes())
	t.Cleanup(srv.Close)
	return srv, up
}

func TestAgentsListsAgentsWithToken(t *testing.T) {
	srv, up := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		io.WriteString(w, `{"agents":[{"id":"demo-data-analyst","description":"Analyst"},{"name":"projects/p/locations/global/agents/other"}]}`)
	})
	resp, err := http.Get(srv.URL + "/api/agents")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var got []agentSummary
	if err := json.NewDecoder(resp.Body).Decode(&got); err != nil {
		t.Fatal(err)
	}
	if len(got) != 2 || got[0].ID != "demo-data-analyst" || got[1].ID != "other" {
		t.Fatalf("unexpected agents: %+v", got)
	}
	r := up.requests[0]
	if r.URL.Path != "/agents-api/agents" {
		t.Errorf("path = %s", r.URL.Path)
	}
	if r.Header.Get("Authorization") != "Bearer secret-token" {
		t.Errorf("missing token")
	}
	if r.Header.Get("X-Goog-User-Project") != "test-project" {
		t.Errorf("missing user project header")
	}
}

func TestInteractionsStreamsEventsAndBuildsBody(t *testing.T) {
	stream := "event: interaction.created\ndata: {\"interaction\":{\"id\":\"i1\"}}\n\nevent: interaction.completed\ndata: {\"interaction\":{\"id\":\"i1\",\"environment_id\":\"env\"}}\n\n"
	srv, up := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		io.WriteString(w, stream)
	})
	body := `{"agent":"demo-data-analyst","input":"Hello","previousInteractionId":"i0","environmentId":"env0"}`
	resp, err := http.Post(srv.URL+"/api/interactions", "application/json", strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	got, _ := io.ReadAll(resp.Body)
	if string(got) != stream {
		t.Fatalf("stream changed:\n%s", got)
	}
	if ct := resp.Header.Get("Content-Type"); ct != "text/event-stream" {
		t.Errorf("content type = %s", ct)
	}
	var sent map[string]any
	if err := json.Unmarshal([]byte(up.bodies[0]), &sent); err != nil {
		t.Fatal(err)
	}
	if sent["agent"] != "demo-data-analyst" || sent["stream"] != true || sent["store"] != true {
		t.Errorf("bad body: %v", sent)
	}
	if sent["previous_interaction_id"] != "i0" || sent["environment"] != "env0" {
		t.Errorf("session fields missing: %v", sent)
	}
	input := sent["input"].([]any)[0].(map[string]any)
	text := input["content"].([]any)[0].(map[string]any)["text"]
	if text != "Hello" {
		t.Errorf("input text = %v", text)
	}
	if up.requests[0].Header.Get("Api-Revision") == "" {
		t.Errorf("missing Api-Revision header")
	}
}

func TestInteractionsRejectsBadRequest(t *testing.T) {
	srv, up := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {})
	for _, body := range []string{`{"agent":"","input":"x"}`, `{"agent":"a","input":""}`, `not json`} {
		resp, err := http.Post(srv.URL+"/api/interactions", "application/json", strings.NewReader(body))
		if err != nil {
			t.Fatal(err)
		}
		resp.Body.Close()
		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("body %q: status %d", body, resp.StatusCode)
		}
	}
	if len(up.requests) != 0 {
		t.Errorf("bad requests reached the upstream")
	}
}

func TestOutputsListsFilesAndSkipsFolder(t *testing.T) {
	srv, up := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		io.WriteString(w, `{"items":[{"name":"agent/output/","size":"0"},{"name":"agent/output/report.md","size":"1970","contentType":"text/markdown"}]}`)
	})
	resp, err := http.Get(srv.URL + "/api/outputs")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var got []outputFile
	json.NewDecoder(resp.Body).Decode(&got)
	if len(got) != 1 || got[0].Name != "agent/output/report.md" || got[0].Size != 1970 {
		t.Fatalf("unexpected outputs: %+v", got)
	}
	r := up.requests[0]
	if r.URL.Path != "/storage/b/test-bucket/o" || r.URL.Query().Get("prefix") != "agent/output/" {
		t.Errorf("bad upstream request: %s", r.URL.String())
	}
}

func TestOutputFileReturnsContent(t *testing.T) {
	srv, up := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "image/png")
		io.WriteString(w, "PNGDATA")
	})
	resp, err := http.Get(srv.URL + "/api/outputs/file?name=agent/output/chart.png")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	got, _ := io.ReadAll(resp.Body)
	if string(got) != "PNGDATA" || resp.Header.Get("Content-Type") != "image/png" {
		t.Fatalf("got %q %s", got, resp.Header.Get("Content-Type"))
	}
	r := up.requests[0]
	if r.URL.Query().Get("alt") != "media" || !strings.HasSuffix(r.URL.EscapedPath(), "/o/agent%2Foutput%2Fchart.png") {
		t.Errorf("bad upstream request: %s", r.URL.String())
	}
}

func TestOutputFileRejectsOtherNames(t *testing.T) {
	srv, up := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {})
	for _, name := range []string{"agent/AGENTS.md", "agent/output/../data/sales.csv", "", "agent/output/"} {
		resp, err := http.Get(srv.URL + "/api/outputs/file?name=" + name)
		if err != nil {
			t.Fatal(err)
		}
		resp.Body.Close()
		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("name %q: status %d", name, resp.StatusCode)
		}
	}
	if len(up.requests) != 0 {
		t.Errorf("rejected names reached the upstream")
	}
}

func TestUpstreamErrorIsPassedThrough(t *testing.T) {
	srv, _ := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusForbidden)
		io.WriteString(w, `{"error":{"message":"Permission denied"}}`)
	})
	resp, err := http.Get(srv.URL + "/api/agents")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	got, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusForbidden || !strings.Contains(string(got), "Permission denied") {
		t.Fatalf("status %d body %s", resp.StatusCode, got)
	}
}

func TestTokenIsNeverSentToBrowser(t *testing.T) {
	srv, _ := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		io.WriteString(w, `{"agents":[]}`)
	})
	resp, err := http.Get(srv.URL + "/api/config")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	got, _ := io.ReadAll(resp.Body)
	if strings.Contains(string(got), "secret-token") {
		t.Fatalf("token in response: %s", got)
	}
	if !strings.Contains(string(got), "test-bucket") {
		t.Fatalf("config missing bucket: %s", got)
	}
}

func TestLoadConfig(t *testing.T) {
	t.Setenv("GOOGLE_CLOUD_PROJECT", "")
	if _, err := LoadConfig(); err == nil {
		t.Fatal("expected an error without GOOGLE_CLOUD_PROJECT")
	}
	t.Setenv("GOOGLE_CLOUD_PROJECT", "p")
	t.Setenv("DEMO_BUCKET", "")
	t.Setenv("PORT", "")
	cfg, err := LoadConfig()
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Bucket != "p-managed-agents-demo" || cfg.Port != "8080" {
		t.Fatalf("defaults wrong: %+v", cfg)
	}
	if cfg.AgentsBase != "https://aiplatform.googleapis.com/v1beta1/projects/p/locations/global" {
		t.Fatalf("agents base: %s", cfg.AgentsBase)
	}
}
