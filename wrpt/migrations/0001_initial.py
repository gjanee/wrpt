# Generated by Django 2.1.7 on 2019-03-02 05:45

from django.conf import settings
import django.contrib.auth.models
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import wrpt.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0009_alter_user_last_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Classroom',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='An identifying name for the classroom.  Ex: 3C, Johnson, 3C Johnson.  If not tallying by classroom, create one classroom named "entire school".', max_length=100, validators=[wrpt.models.notBlankValidator])),
                ('enrollment', models.IntegerField(help_text='Number of students in the classroom', validators=[django.core.validators.MinValueValidator(1)])),
            ],
        ),
        migrations.CreateModel(
            name='Count',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.IntegerField(blank=True, help_text='Total number of students who took alternative transportation', null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('activeValue', models.IntegerField(blank=True, help_text='Number of students who walked/biked/scootered/etc', null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('inactiveValue', models.IntegerField(blank=True, help_text='Number of students who carpooled/bused', null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('absentees', models.IntegerField(default=0, help_text='Number of students absent', validators=[django.core.validators.MinValueValidator(0)])),
                ('comments', models.CharField(blank=True, max_length=1000)),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wrpt.Classroom')),
            ],
        ),
        migrations.CreateModel(
            name='EventDate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.CharField(help_text='Ex: Jan, Apr #2, Mar 17', max_length=10, validators=[wrpt.models.notBlankValidator])),
                ('seq', models.IntegerField(blank=True, help_text='Defines the order of dates in the schedule; leave blank to order as given')),
            ],
        ),
        migrations.CreateModel(
            name='Program',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('schoolYear', models.CharField(help_text='Ex: 2013-2014', max_length=9, validators=[wrpt.models.schoolYearValidator], verbose_name='School year')),
                ('splitCounts', models.BooleanField(help_text='Check to split participation counts into two parts, active (walk/bike/scooter/etc) and inactive (carpool/bus)', verbose_name='Split counts')),
                ('participationGoal', models.IntegerField(blank=True, help_text='Ex: 50', null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Participation goal (percentage; optional)')),
            ],
            options={
                'verbose_name_plural': ' Programs',
            },
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Ex: Monthly, Bi-monthly, Wednesdays 2013-2014, Adams 2013-2014', max_length=100, unique=True, validators=[wrpt.models.notBlankValidator])),
            ],
            options={
                'verbose_name_plural': '  Schedules',
            },
        ),
        migrations.CreateModel(
            name='School',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Ex: Adams, Goleta Valley JH', max_length=100, unique=True, validators=[wrpt.models.notBlankValidator])),
            ],
            options={
                'verbose_name_plural': '   Schools',
            },
        ),
        migrations.CreateModel(
            name='WrptUser',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('school', models.ForeignKey(blank=True, help_text='The school that this user can update.  Set for non-staff users only.', null=True, on_delete=django.db.models.deletion.CASCADE, to='wrpt.School')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': '     Users',
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AddField(
            model_name='program',
            name='schedule',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wrpt.Schedule'),
        ),
        migrations.AddField(
            model_name='program',
            name='school',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wrpt.School'),
        ),
        migrations.AddField(
            model_name='eventdate',
            name='schedule',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wrpt.Schedule'),
        ),
        migrations.AddField(
            model_name='count',
            name='eventDate',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wrpt.EventDate', verbose_name='Event date'),
        ),
        migrations.AddField(
            model_name='count',
            name='program',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wrpt.Program'),
        ),
        migrations.AddField(
            model_name='classroom',
            name='program',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wrpt.Program'),
        ),
        migrations.AlterUniqueTogether(
            name='program',
            unique_together={('school', 'schoolYear')},
        ),
        migrations.AlterUniqueTogether(
            name='eventdate',
            unique_together={('schedule', 'date')},
        ),
        migrations.AlterUniqueTogether(
            name='count',
            unique_together={('program', 'eventDate', 'classroom')},
        ),
        migrations.AlterUniqueTogether(
            name='classroom',
            unique_together={('program', 'name')},
        ),
    ]
