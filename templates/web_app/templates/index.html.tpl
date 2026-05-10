<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$title</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f0f0f;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .header {
            background: #1a1a2e;
            padding: 16px 24px;
            border-bottom: 1px solid #2a2a3e;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header h1 {
            font-size: 18px;
            color: #00d4ff;
            font-weight: 600;
        }
        .header .subtitle {
            font-size: 13px;
            color: #888;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
        }
        .card {
            background: #1a1a2e;
            border: 1px solid #2a2a3e;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
        }
        input, select, textarea {
            background: #0f0f0f;
            border: 1px solid #2a2a3e;
            border-radius: 6px;
            padding: 10px 14px;
            color: #e0e0e0;
            font-size: 14px;
            outline: none;
            width: 100%;
        }
        input:focus, select:focus, textarea:focus {
            border-color: #00d4ff;
        }
        button {
            background: #00d4ff;
            color: #0f0f0f;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover {
            background: #00b8d9;
        }
        button.secondary {
            background: #2a2a3e;
            color: #e0e0e0;
        }
        button.secondary:hover {
            background: #3a3a4e;
        }
        .result {
            margin-top: 16px;
            padding: 16px;
            background: #0f0f0f;
            border-radius: 6px;
            border: 1px solid #2a2a3e;
        }
        .error {
            color: #ff4757;
            background: rgba(255, 71, 87, 0.1);
            border-color: #ff4757;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            text-align: left;
            padding: 10px 14px;
            border-bottom: 1px solid #2a2a3e;
        }
        th {
            color: #00d4ff;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
        }
        a {
            color: #00d4ff;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-green { background: rgba(46, 213, 115, 0.2); color: #2ed573; }
        .badge-red { background: rgba(255, 71, 87, 0.2); color: #ff4757; }
        .badge-yellow { background: rgba(255, 165, 2, 0.2); color: #ffa502; }
        .badge-blue { background: rgba(0, 212, 255, 0.2); color: #00d4ff; }
        $css_styles
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>$title</h1>
            <div class="subtitle">$description</div>
        </div>
    </div>
    <div class="container">
        $html_body
    </div>
    <script>
        $javascript
    </script>
</body>
</html>
