# syntax=docker/dockerfile:1.7

FROM golang:1.22-alpine AS builder

WORKDIR /app

RUN apk add --no-cache git

COPY go.mod go.sum ./

RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

COPY . .

RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags="-s -w" -o /out/pharmacy ./cmd/pharmacy/main.go

RUN test -s /out/pharmacy

FROM alpine:3.19 AS runtime

WORKDIR /app

RUN apk add --no-cache curl \
    && addgroup -S app \
    && adduser -S app -G app

COPY --from=builder --chown=app:app /out/pharmacy /app/pharmacy

USER app

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

EXPOSE 8081

CMD ["./pharmacy"]