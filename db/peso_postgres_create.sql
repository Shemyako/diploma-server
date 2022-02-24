CREATE TABLE "public.types_of_lessons" (
	"id" serial NOT NULL,
	"name" varchar(255) NOT NULL,
	"from_client" float8,
	"for_instructor" float8,
	"is_visible" bool NOT NULL,
	CONSTRAINT "types_of_lessons_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE "public.dogs" (
	"id" serial NOT NULL,
	"name" varchar(50) NOT NULL,
	"breed" varchar(20) NOT NULL,
	"is_all" bool NOT NULL,
	"staff_id" int,
	"place_for_lesson" int NOT NULL,
	CONSTRAINT "dogs_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE "public.users_dog" (
	"id" serial NOT NULL,
	"user_id" int NOT NULL,
	"dog_id" int NOT NULL,
	CONSTRAINT "users_dog_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE "public.lesson" (
	"id" serial NOT NULL,
	"date" TIMESTAMP NOT NULL,
	"dog_id" int NOT NULL,
	"place_id" int NOT NULL,
	"type_of_lesson" int NOT NULL,
	"staff_id" int NOT NULL,
	CONSTRAINT "lesson_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE "public.staff" (
	"id" serial NOT NULL,
	"name" varchar(255) NOT NULL,
	"role" int NOT NULL,
	"phone" varchar(13) NOT NULL,
	"date_of_birth" DATE,
	"tg_id" int,
	"allowed_to" int DEFAULT '0',
	"e-mail" varchar(255),
	CONSTRAINT "staff_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE "public.places" (
	"id" serial NOT NULL,
	"address" varchar(255) NOT NULL,
	"name" varchar(255) NOT NULL,
	"is_actual" bool NOT NULL,
	CONSTRAINT "places_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE "public.advertisement" (
	"id" serial NOT NULL,
	"created_by" int NOT NULL,
	"date_to_post" TIMESTAMP NOT NULL,
	"text" varchar(255) NOT NULL,
	"file" varchar(255) NOT NULL,
	CONSTRAINT "advertisement_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE "public.user" (
	"id" serial NOT NULL,
	"password" varchar(255) NOT NULL,
	"staff_id" int NOT NULL,
	CONSTRAINT "user_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE "public.courses" (
	"id" serial NOT NULL,
	"name" varchar(255) NOT NULL,
	"amount" int NOT NULL,
	"price" float4 NOT NULL,
	"is_actual" bool NOT NULL,
	CONSTRAINT "courses_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE "public.dog_cours" (
	"id" serial NOT NULL,
	"dog_id" int NOT NULL,
	"cours_id" int NOT NULL,
	"date_of_cours" DATE NOT NULL,
	CONSTRAINT "dog_cours_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);



CREATE TABLE "public.sessions" (
	"id" serial NOT NULL,
	"user_id" int NOT NULL,
	"token" varchar(255) NOT NULL,
	"time" bigint NOT NULL,
	"ip" varchar(255) NOT NULL,
	"mac" varchar(255) NOT NULL,
	CONSTRAINT "sessions_pk" PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);




ALTER TABLE "dogs" ADD CONSTRAINT "dogs_fk0" FOREIGN KEY ("staff_id") REFERENCES "staff"("id");
ALTER TABLE "dogs" ADD CONSTRAINT "dogs_fk1" FOREIGN KEY ("place_for_lesson") REFERENCES "places"("id");

ALTER TABLE "users_dog" ADD CONSTRAINT "users_dog_fk0" FOREIGN KEY ("user_id") REFERENCES "staff"("id");
ALTER TABLE "users_dog" ADD CONSTRAINT "users_dog_fk1" FOREIGN KEY ("dog_id") REFERENCES "dogs"("id");

ALTER TABLE "lesson" ADD CONSTRAINT "lesson_fk0" FOREIGN KEY ("dog_id") REFERENCES "dogs"("id");
ALTER TABLE "lesson" ADD CONSTRAINT "lesson_fk1" FOREIGN KEY ("place_id") REFERENCES "places"("id");
ALTER TABLE "lesson" ADD CONSTRAINT "lesson_fk2" FOREIGN KEY ("type_of_lesson") REFERENCES "types_of_lessons"("id");
ALTER TABLE "lesson" ADD CONSTRAINT "lesson_fk3" FOREIGN KEY ("staff_id") REFERENCES "staff"("id");



ALTER TABLE "advertisement" ADD CONSTRAINT "advertisement_fk0" FOREIGN KEY ("created_by") REFERENCES "staff"("id");

ALTER TABLE "user" ADD CONSTRAINT "user_fk0" FOREIGN KEY ("staff_id") REFERENCES "staff"("id");


ALTER TABLE "dog_cours" ADD CONSTRAINT "dog_cours_fk0" FOREIGN KEY ("dog_id") REFERENCES "dogs"("id");
ALTER TABLE "dog_cours" ADD CONSTRAINT "dog_cours_fk1" FOREIGN KEY ("cours_id") REFERENCES "courses"("id");

ALTER TABLE "sessions" ADD CONSTRAINT "sessions_fk0" FOREIGN KEY ("user_id") REFERENCES "user"("id");












