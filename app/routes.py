from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from app.models import Users, Skills, LookupTable
from werkzeug.urls import url_parse
import json

from app import app, db
from app.forms import LoginForm
from sqlalchemy import extract


@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('dashboard')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if current_user.admin == 'Y':
        return render_template('dashboard_admin.html')
    user = Users.query.filter_by(manager_id=current_user.id).first()
    if user is not None:
        return render_template('dashboard_manager.html')
    return render_template('dashboard.html', id=current_user.id)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/update_skill', methods=['GET', 'POST'])
def update_skill():
    x = db.session.query(db.func.max(Skills.skill_id)).group_by(Skills.skill, Skills.employee_id).filter(
        Skills.employee_id == current_user.id).all()
    sk = LookupTable.query.filter_by(field="skill").all()
    print(x)
    print(sk)
    skills = []
    for i in x:
        skills.append(Skills.query.filter_by(skill_id=i[0]).first())
    print(skills)
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if request.method == 'POST':
        data = dict(request.form)
        p = []
        for key in data:
            if "skills" in key:
                p.append(key[6:])
        print(p)
        print(data, x)
        for i in p:
            s = Skills(employee_id=current_user.id, skill=data['skills' + i],
                       skill_exp=data['experience' + i], emp_rating=data['rating' + i], skill_interest=data['interest' + i])
            db.session.add(s)
            db.session.commit()
        return redirect('dashboard')
    return render_template('update_skill.html', title='Update Skill', skills=skills, len=len(skills), s=sk)


@app.route('/search', methods=['GET', 'POST'])
def search():
    sk = LookupTable.query.filter_by(field="skill").all()
    if request.method == 'POST':
        data = dict(request.form)
        z = db.session.query(db.func.max(Skills.skill_id)).group_by(Skills.skill, Skills.employee_id).all()
        print(data)
        print(z)
        t = []
        for key in data:
            if "skills" in key:
                t.append(key[6:])
        print(t)
        flag = []
        ratings_all = []
        for p in t:
            if data['skills' + p] == "any":
                final_res = []
                u = Users.query.filter(Users.admin == 'N').all()
                for i in u:
                    final_res.append((i, 0))
                    print(final_res)
                return render_template('search.html', title='Search', result=final_res, s=sk)
        for p in t:
            rating = {}
            for i in z:
                x = Skills.query.filter_by(skill_id=i[0]).first()
                print(x)
                if x.manager_rating is not None:
                    print("test : ", x.skill_id)
                    if x.skill == data['skills' + p] and x.skill_exp >= int(data['experience' + p]) and (0.4*x.emp_rating + 0.6*x.manager_rating) >= int(data['rating' + p]) and x.skill_interest >= int(data['interest' + p]):
                        print(x.skill_id)
                        rating.update({x.employee_id: (x.emp_rating + x.manager_rating) / 2})
                else:
                    if x.skill == data['skills' + p] and x.skill_exp >= int(
                            data['experience' + p]) and x.emp_rating >= int(data['rating' + p]) and x.skill_interest >= int(data['interest' + p]):
                        rating.update({x.employee_id: (x.emp_rating, x.skill_interest)})
                        flag.append(x.employee_id)
            ratings_all.append(rating)
        print(flag)
        print(ratings_all)
        inter = list(ratings_all[0].keys())
        for i in range(0, len(ratings_all) - 1):
            if i == 0:
                inter = list(set(list(ratings_all[i].keys())) & set(list(ratings_all[i + 1].keys())))
            else:
                inter = list(set(inter) & set(list(ratings_all[i + 1].keys())))
        print(inter)
        final_res = []
        print(ratings_all)
        for i in inter:
            x = Users.query.filter_by(id=i).first()
            r_avg = 0
            i_avg = 0
            for p in ratings_all:
                r_avg = r_avg + p[i][0]
                i_avg = i_avg + p[i][1]
            r_avg = r_avg / len(ratings_all)
            i_avg = i_avg / len(ratings_all)
            y = 0
            for j in flag:
                if i == j:
                    y = 1
                    break
            final_res.append((x, y, i_avg, r_avg))
        print(final_res)
        final_res.sort(key=lambda x: float(x[2]), reverse=True)
        print(final_res)
        return render_template('search.html', result=final_res, s=sk)
    return render_template('search.html', s=sk)


@app.route('/manager_rating', methods=['GET', 'POST'])
def manager_rating():
    q = Users.query.filter_by(manager_id=current_user.id).all()
    print(q)
    if request.method == 'POST':
        data = dict(request.form)
        print(data)
        if data["flag"] == "select":
            u = Users.query.filter_by(id=data['choose_employee']).first()
            q.insert(0, q.pop(q.index(Users.query.filter_by(id=data['choose_employee']).first())))
            name = u.username
            print(u, q)
            x = db.session.query(db.func.max(Skills.skill_id)).group_by(Skills.skill, Skills.employee_id).filter(
                Skills.employee_id == data['choose_employee']).all()
            print(x)
            s = []
            for i in x:
                s.append(Skills.query.filter_by(skill_id=i[0]).first())
            print(s)
            return render_template('manager_rating.html', emp=q, skills=s, name=name, flag=1)
        else:
            u = Users.query.filter_by(id=data['choose_employee']).first()
            name = u.username
            x = db.session.query(db.func.max(Skills.skill_id)).group_by(Skills.skill, Skills.employee_id).filter(
                Skills.employee_id == data['choose_employee']).all()
            print(x)
            s = []
            for i in x:
                s.append(Skills.query.filter_by(skill_id=i[0]).first())
            for j in s:
                rating = data['manager_rating' + str(j.skill_id)]
                if rating == "None":
                    j.manager_rating = None
                else:
                    j.manager_rating = rating
                print(rating)
                db.session.commit()
            return render_template('manager_rating.html', emp=q, skills=s, name=name, flag=0)
    return render_template('manager_rating.html', emp=q, flag=0)


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    username = db.session.query(Users.username).filter_by(id=current_user.id).first()
    location = db.session.query(Users.location).filter_by(id=current_user.id).first()
    print(username, location)
    if request.method == 'POST':
        u = Users.query.filter_by(id=current_user.id).first()
        new_name = request.form.get('username')
        new_pass = request.form.get('confirm_pw')
        print(new_name, new_pass)
        u.username = new_name
        u.set_password(new_pass)
        db.session.commit()
        return redirect('dashboard')
    return render_template('edit_profile.html', name=username[0], loc=location[0])


@app.route('/overall_statistics')
def overall_stats():
    x = db.session.query(Skills.skill, db.func.count(Skills.employee_id.distinct())).group_by(Skills.skill).all()
    print(x)
    data = [['Tech', 'No. of ppl']]
    for i in x:
        data.append([i[0], i[1]])
    print(data)
    y = db.session.query(Skills.skill, db.func.count(Skills.employee_id.distinct())).group_by(Skills.skill).all()
    print(y)
    data1 = [
        ['Year', 'Python', 'Java', 'HTML'],
        ['2014', 4.5, 3.9, 4.2],
        ['2015', 4.5, 3.7, 4.3],
        ['2016', 3.9, 4.0, 4.4],
        ['2017', 3.9, 3.8, 4.5]
    ]
    loc = [['Task', 'Hours per Day'],
           ['Work', 11],
           ['Eat', 2],
           ['Commute', 2],
           ['Watch TV', 2],
           ['Sleep', 7]]

    prac = [
        ["Element", "Density", { 'role': "style" } ],
        ["Copper", 8.94, "#b87333"],
        ["Silver", 10.49, "silver"],
        ["Gold", 19.30, "gold"],
        ["Platinum", 21.45, "color: #e5e4e2"]
      ]
    print(json.dumps(data1))
    return render_template('overall_stats.html', data=json.dumps(data), data1=json.dumps(data1), loc=json.dumps(loc),
                           prac=json.dumps(prac))


@app.route('/emp_stats/<string:id>', methods=['GET', 'POST'])
def emp_stats(id):
    print(id)
    d = db.session.query(Skills.skill.distinct()).filter_by(employee_id=id).order_by(Skills.skill_id).all()
    t = db.session.query(extract('year', Skills.timestamp), extract('month', Skills.timestamp),
                         extract('day', Skills.timestamp), Skills.skill, Skills.emp_rating, Skills.manager_rating).filter_by(
        employee_id=id).order_by(Skills.skill_id).all()
    res = [['time']]
    for i in d:
        res[0].append(i[0])
    print(res)
    x = [0] * len(res[0])
    print(t)
    for i in t:
        x[0] = (i[0], i[1], i[2])
        if i[5] is not None:
            x[res[0].index(i[3])] = 0.4*i[4]+0.6*i[5]
        else:
            x[res[0].index(i[3])] = i[4]
        res.append(x[:])
    print(res)
    final_res = []
    for i in range(0, len(res)):
        if i == len(res) - 1:
            final_res.append(res[i])
            break
        if res[i][0] != res[i + 1][0]:
            final_res.append(res[i])
    print(final_res)
    return render_template('emp_stat.html', data=json.dumps(final_res))


@app.route('/new_employee', methods=['GET', 'POST'])
def new_employee():
    e = Users.query.filter_by(admin='N').all()
    loc = LookupTable.query.filter_by(field="location").all()
    pra = LookupTable.query.filter_by(field="practice").all()
    if request.method == 'POST':
        details = dict(request.form)
        print(details)
        e = Users(id=details['id'], username=details['username'], email=details['mail'], location=details['location'],
                  practice=details['practice'], manager_id=details['manager_id'])
        e.set_password('1234')
        db.session.add(e)
        db.session.commit()
        return render_template('new_employee.html', emp=e, l=loc, p=pra)
    return render_template('new_employee.html', emp=e, l=loc, p=pra)


@app.route('/edit_emp', methods=['GET', 'POST'])
def edit_emp():
    users = Users.query.filter_by(admin='N').all()
    loc = LookupTable.query.filter_by(field="location").all()
    pra = LookupTable.query.filter_by(field="practice").all()
    if request.method == "POST":
        data = dict(request.form)
        print(data)
        u = Users.query.filter_by(id=data["id"]).first()
        if data["flag"] == "select":
            print(u)
            users.insert(0, users.pop(users.index(Users.query.filter_by(id=data['id']).first())))
            return render_template('edit_emp.html', emp=users, flag=1, u=u, l=loc, p=pra)
        if data["flag"] == "submit":
            u.location = data["location"]
            u.practice = data["practice"]
            u.manager_id = data["manager_id"]
            db.session.commit()
        return render_template('edit_emp.html', emp=users, flag=0)
    return render_template('edit_emp.html', emp=users, flag=0)


@app.route('/add_fields', methods=['GET', 'POST'])
def add_fields():
    skills = LookupTable.query.filter_by(field="skill").all()
    loc = LookupTable.query.filter_by(field="location").all()
    pra = LookupTable.query.filter_by(field="practice").all()
    print(skills)
    if request.method == "POST":
        data = dict(request.form)
        print(data)
        if data["flag"] == "skills":
            db.session.query(LookupTable).filter_by(field="skill").delete()
            for key in data:
                if key != "flag":
                    s = LookupTable(value=data[key], field='skill')
                    db.session.add(s)
            db.session.commit()
            new_skills = LookupTable.query.filter_by(field="skill").all()
            return render_template('add_fields.html', skills=new_skills, s=len(new_skills), loc=loc, pra=pra,
                                   l=len(loc), p=len(pra))
        if data["flag"] == "location":
            db.session.query(LookupTable).filter_by(field="location").delete()
            for key in data:
                if key != "flag":
                    s = LookupTable(value=data[key], field='location')
                    db.session.add(s)
            db.session.commit()
            new_loc = LookupTable.query.filter_by(field="location").all()
            return render_template('add_fields.html', skills=skills, s=len(skills), loc=new_loc, pra=pra,
                                   l=len(new_loc), p=len(pra))
        if data["flag"] == "practice":
            db.session.query(LookupTable).filter_by(field="practice").delete()
            for key in data:
                if key != "flag":
                    s = LookupTable(value=data[key], field='practice')
                    db.session.add(s)
            db.session.commit()
            new_pra = LookupTable.query.filter_by(field="practice").all()
            return render_template('add_fields.html', skills=skills, s=len(skills), loc=loc, pra=new_pra,
                                   l=len(loc), p=len(new_pra))
    return render_template('add_fields.html', skills=skills, loc=loc, pra=pra, s=len(skills), l=len(loc), p=len(pra))
