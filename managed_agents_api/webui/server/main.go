// Command server is a small local web UI for the Managed Agents API demo.
//
// The server holds the Google credentials. The browser never gets a token. The server
// lists the agents, starts interactions and passes the event stream to the browser, and
// lists and returns the files that the agent wrote to the demo bucket.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"path"
	"strconv"
	"strings"
	"time"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
)

const (
	outputPrefix = "agent/output/"
	apiRevision  = "2026-05-20"
)

// Config holds the server settings.
type Config struct {
	Project     string
	Bucket      string
	Port        string
	StaticDir   string
	AgentsBase  string
	StorageBase string
}

// LoadConfig reads the settings from the environment.
func LoadConfig() (Config, error) {
	project := strings.TrimSpace(os.Getenv("GOOGLE_CLOUD_PROJECT"))
	if project == "" {
		return Config{}, errors.New("GOOGLE_CLOUD_PROJECT is not set. Set it to your project ID")
	}
	cfg := Config{
		Project:     project,
		Bucket:      envOr("DEMO_BUCKET", project+"-managed-agents-demo"),
		Port:        envOr("PORT", "8080"),
		StaticDir:   envOr("STATIC_DIR", "../web"),
		AgentsBase:  "https://aiplatform.googleapis.com/v1beta1/projects/" + project + "/locations/global",
		StorageBase: "https://storage.googleapis.com/storage/v1",
	}
	return cfg, nil
}

func envOr(key, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(key)); value != "" {
		return value
	}
	return fallback
}

// Server serves the API and the static frontend.
type Server struct {
	cfg    Config
	tokens oauth2.TokenSource
	http   *http.Client
}

// NewServer returns a server. The token source gives the Google access tokens.
func NewServer(cfg Config, tokens oauth2.TokenSource, client *http.Client) *Server {
	return &Server{cfg: cfg, tokens: tokens, http: client}
}

// Routes returns the HTTP handler.
func (s *Server) Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/config", s.handleConfig)
	mux.HandleFunc("GET /api/agents", s.handleAgents)
	mux.HandleFunc("POST /api/interactions", s.handleInteractions)
	mux.HandleFunc("GET /api/outputs", s.handleOutputs)
	mux.HandleFunc("GET /api/outputs/file", s.handleOutputFile)
	mux.Handle("GET /", http.FileServer(http.Dir(s.cfg.StaticDir)))
	return mux
}

// upstream sends a request to a Google API with the access token.
func (s *Server) upstream(ctx context.Context, method, target string, body io.Reader) (*http.Response, error) {
	token, err := s.tokens.Token()
	if err != nil {
		return nil, fmt.Errorf("get an access token: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, method, target, body)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+token.AccessToken)
	req.Header.Set("X-Goog-User-Project", s.cfg.Project)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	return s.http.Do(req)
}

// passError copies an upstream error to the browser, and returns true if there was one.
func passError(w http.ResponseWriter, resp *http.Response) bool {
	if resp.StatusCode < 400 {
		return false
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
	return true
}

func writeJSON(w http.ResponseWriter, value any) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(value)
}

func (s *Server) handleConfig(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]string{"project": s.cfg.Project, "bucket": s.cfg.Bucket})
}

type agentSummary struct {
	ID          string `json:"id"`
	Description string `json:"description"`
}

func (s *Server) handleAgents(w http.ResponseWriter, r *http.Request) {
	resp, err := s.upstream(r.Context(), http.MethodGet, s.cfg.AgentsBase+"/agents?page_size=100", nil)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	if passError(w, resp) {
		return
	}
	var page struct {
		Agents []struct {
			ID          string `json:"id"`
			Name        string `json:"name"`
			Description string `json:"description"`
		} `json:"agents"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&page); err != nil {
		http.Error(w, "read the agent list: "+err.Error(), http.StatusBadGateway)
		return
	}
	agents := []agentSummary{}
	for _, a := range page.Agents {
		id := a.ID
		if id == "" {
			id = path.Base(a.Name)
		}
		agents = append(agents, agentSummary{ID: id, Description: a.Description})
	}
	writeJSON(w, agents)
}

type interactionRequest struct {
	Agent                 string `json:"agent"`
	Input                 string `json:"input"`
	PreviousInteractionID string `json:"previousInteractionId"`
	EnvironmentID         string `json:"environmentId"`
}

func (s *Server) handleInteractions(w http.ResponseWriter, r *http.Request) {
	var in interactionRequest
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		http.Error(w, "the request body is not valid JSON", http.StatusBadRequest)
		return
	}
	if strings.TrimSpace(in.Agent) == "" || strings.TrimSpace(in.Input) == "" {
		http.Error(w, "agent and input are required", http.StatusBadRequest)
		return
	}
	body := map[string]any{
		"agent":      in.Agent,
		"stream":     true,
		"background": true,
		"store":      true,
		"input": []any{map[string]any{
			"type":    "user_input",
			"content": []any{map[string]any{"type": "text", "text": in.Input}},
		}},
	}
	if in.PreviousInteractionID != "" {
		body["previous_interaction_id"] = in.PreviousInteractionID
	}
	if in.EnvironmentID != "" {
		body["environment"] = in.EnvironmentID
	}
	payload, _ := json.Marshal(body)

	token, err := s.tokens.Token()
	if err != nil {
		http.Error(w, "get an access token: "+err.Error(), http.StatusBadGateway)
		return
	}
	req, err := http.NewRequestWithContext(r.Context(), http.MethodPost, s.cfg.AgentsBase+"/interactions", strings.NewReader(string(payload)))
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	req.Header.Set("Authorization", "Bearer "+token.AccessToken)
	req.Header.Set("X-Goog-User-Project", s.cfg.Project)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Api-Revision", apiRevision)
	resp, err := s.http.Do(req)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	if passError(w, resp) {
		return
	}

	// Pass the server-sent events to the browser without change. Flush after each read,
	// so that the browser shows each step when it arrives.
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	flusher, _ := w.(http.Flusher)
	buf := make([]byte, 4096)
	for {
		n, readErr := resp.Body.Read(buf)
		if n > 0 {
			if _, err := w.Write(buf[:n]); err != nil {
				return
			}
			if flusher != nil {
				flusher.Flush()
			}
		}
		if readErr != nil {
			return
		}
	}
}

type outputFile struct {
	Name        string `json:"name"`
	Size        int64  `json:"size"`
	ContentType string `json:"contentType"`
	Updated     string `json:"updated"`
}

func (s *Server) handleOutputs(w http.ResponseWriter, r *http.Request) {
	target := fmt.Sprintf("%s/b/%s/o?prefix=%s", s.cfg.StorageBase, url.PathEscape(s.cfg.Bucket), url.QueryEscape(outputPrefix))
	resp, err := s.upstream(r.Context(), http.MethodGet, target, nil)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	if passError(w, resp) {
		return
	}
	var page struct {
		Items []struct {
			Name        string `json:"name"`
			Size        string `json:"size"`
			ContentType string `json:"contentType"`
			Updated     string `json:"updated"`
		} `json:"items"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&page); err != nil {
		http.Error(w, "read the object list: "+err.Error(), http.StatusBadGateway)
		return
	}
	files := []outputFile{}
	for _, item := range page.Items {
		// The sandbox creates a zero-byte object for the folder itself.
		if strings.HasSuffix(item.Name, "/") {
			continue
		}
		size, _ := strconv.ParseInt(item.Size, 10, 64)
		files = append(files, outputFile{Name: item.Name, Size: size, ContentType: item.ContentType, Updated: item.Updated})
	}
	writeJSON(w, files)
}

// validOutputName accepts only files directly or deeper under agent/output/, with no "..".
func validOutputName(name string) bool {
	if !strings.HasPrefix(name, outputPrefix) || len(name) == len(outputPrefix) {
		return false
	}
	return path.Clean(name) == name && !strings.Contains(name, "..")
}

func (s *Server) handleOutputFile(w http.ResponseWriter, r *http.Request) {
	name := r.URL.Query().Get("name")
	if !validOutputName(name) {
		http.Error(w, "name must be a file under "+outputPrefix, http.StatusBadRequest)
		return
	}
	target := fmt.Sprintf("%s/b/%s/o/%s?alt=media", s.cfg.StorageBase, url.PathEscape(s.cfg.Bucket), url.PathEscape(name))
	resp, err := s.upstream(r.Context(), http.MethodGet, target, nil)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	if passError(w, resp) {
		return
	}
	if ct := resp.Header.Get("Content-Type"); ct != "" {
		w.Header().Set("Content-Type", ct)
	}
	io.Copy(w, resp.Body)
}

func main() {
	cfg, err := LoadConfig()
	if err != nil {
		log.Fatal(err)
	}
	ctx := context.Background()
	tokens, err := google.DefaultTokenSource(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		log.Fatalf("Application Default Credentials are not available: %v. Run: gcloud auth application-default login", err)
	}
	server := NewServer(cfg, tokens, &http.Client{Timeout: 15 * time.Minute})
	addr := ":" + cfg.Port
	log.Printf("Managed Agents demo UI on http://localhost%s (project %s, bucket %s)", addr, cfg.Project, cfg.Bucket)
	log.Fatal(http.ListenAndServe(addr, server.Routes()))
}
