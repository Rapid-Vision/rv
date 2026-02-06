// THIS CODE IS GENERATED

package rpcclient

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
)

func (c *RPCClient) doRequest(ctx context.Context, path string, payload any, out any) error {
	if ctx == nil {
		ctx = context.Background()
	}
	url := c.baseURL + path
	var body io.Reader
	if payload != nil {
		raw, err := json.Marshal(payload)
		if err != nil {
			return fmt.Errorf("encode payload: %w", err)
		}
		body = bytes.NewReader(raw)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, body)
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if c.bearerToken != "" {
		hasAuthHeader := false
		for key := range c.headers {
			if http.CanonicalHeaderKey(key) == "Authorization" {
				hasAuthHeader = true
				break
			}
		}
		if !hasAuthHeader {
			req.Header.Set("Authorization", "Bearer "+c.bearerToken)
		}
	}
	for key, value := range c.headers {
		req.Header.Set(key, value)
	}
	resp, err := c.client.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("read response: %w", err)
	}
	if resp.StatusCode < http.StatusOK || resp.StatusCode >= http.StatusMultipleChoices {
		if len(raw) > 0 {
			var rpcErr RPCError
			if err := json.Unmarshal(raw, &rpcErr); err == nil && rpcErr.Type != "" {
				return errorFromRPCError(rpcErr)
			}
			if strings.TrimSpace(string(raw)) != "" {
				return ErrHTTP{Status: resp.StatusCode, Body: strings.TrimSpace(string(raw))}
			}
		}
		return ErrHTTP{Status: resp.StatusCode}
	}
	if out == nil || len(raw) == 0 {
		return nil
	}
	if err := json.Unmarshal(raw, out); err != nil {
		return fmt.Errorf("decode response: %w", err)
	}
	return nil
}
