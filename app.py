@app.route("/admin")
def admin():
    skins = []
    if session.get("admin"):
        with connect() as con:
            skins = con.execute(
                "SELECT * FROM skins ORDER BY id DESC"
            ).fetchall()

    return render_template("admin.html", skins=skins)
