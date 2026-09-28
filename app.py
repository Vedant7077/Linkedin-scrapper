from flask import Flask, request, jsonify
from scraper import scrape_profile

app = Flask(__name__)

@app.route("/scrape", methods=["POST"])
def scrape():
    try:
        data = request.json
        profile_urls = data.get("profiles", [])
        username = data.get("username")  # Optional credentials
        password = data.get("password")  # Optional credentials
        
        if not profile_urls:
            return jsonify({
                "status": "error",
                "message": "No profile URLs provided"
            }), 400

        results = []
        for url in profile_urls:
            if not url.startswith("https://www.linkedin.com/in/"):
                results.append({
                    "profile_url": url,
                    "status": "error",
                    "message": "Invalid LinkedIn profile URL"
                })
                continue
            
            # Pass credentials if provided
            profile_data = scrape_profile(url, username=username, password=password)
            results.append(profile_data)

        # Check if we have any successful results
        successful_results = [r for r in results if r.get("status") != "error"]
        
        return jsonify({
            "status": "success" if successful_results else "error",
            "count": len(results),
            "successful": len(successful_results),
            "data": results
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "message": "LinkedIn scraper is running"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)