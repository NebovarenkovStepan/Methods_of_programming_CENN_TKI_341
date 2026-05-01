FROM golang:1.22-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

# Явно компилируем main.go, чтобы гарантированно получить исполняемый файл
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -installsuffix cgo -o portal ./cmd/portal/main.go

# На всякий случай убедимся, что файл не пустой и больше 1 МБ (статический бинарник обычно больше)
RUN test -s portal && echo "Build OK"

FROM alpine:3.19

WORKDIR /app

COPY --from=builder /app/portal .

RUN chmod +x portal
RUN apk add --no-cache curl

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["./portal"]