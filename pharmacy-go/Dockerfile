FROM golang:1.22-alpine

WORKDIR /app
RUN apk add --no-cache curl git
COPY go.mod go.sum ./
RUN go mod download
COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o pharmacy ./cmd/pharmacy/main.go
RUN chmod +x pharmacy

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

EXPOSE 8081

CMD ["./pharmacy"]