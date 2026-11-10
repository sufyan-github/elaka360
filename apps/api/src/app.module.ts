import { Module } from '@nestjs/common';
import { APP_FILTER, APP_GUARD } from '@nestjs/core';
import { ThrottlerGuard, ThrottlerModule } from '@nestjs/throttler';
import { DbModule } from './db/db.module';
import { ProblemFilter } from './common/problem.filter';
import { AuthGuard } from './common/auth/auth.guard';
import { GeoController } from './geo/geo.controller';
import { GeoService } from './geo/geo.service';
import { CategoriesController } from './categories/categories.controller';
import { PlacesController } from './places/places.controller';
import { PlacesService } from './places/places.service';
import { EmergencyController } from './emergency/emergency.controller';
import { SearchController } from './search/search.controller';
import { SearchService } from './search/search.service';
import { HealthController } from './health/health.controller';
import { AuthController } from './auth/auth.controller';
import { AuthService } from './auth/auth.service';
import { MeController } from './me/me.controller';
import { ReviewsController } from './reviews/reviews.controller';
import { ContributionsController } from './contributions/contributions.controller';
import { ContributionsService } from './contributions/contributions.service';
import { AdminAreasController } from './admin/admin-areas.controller';
import { AdminPlacesController } from './admin/admin-places.controller';
import { AdminModerationController } from './admin/admin-moderation.controller';
import { AdminSourcesUsersController } from './admin/admin-sources-users.controller';
import { ContactController } from './content/contact.controller';
import { MfaController } from './auth/mfa.controller';
import { DuplicatesController } from './quality/duplicates.controller';
import { ApiKeyGuard, ApiKeysController, OpenDataController } from './opendata/opendata.controller';

@Module({ controllers: [GeoController], providers: [GeoService], exports: [GeoService] })
export class GeoModule {}

@Module({ controllers: [CategoriesController, PlacesController, EmergencyController, ReviewsController], providers: [PlacesService], exports: [PlacesService] })
export class PlacesModule {}

@Module({ controllers: [SearchController, HealthController], providers: [SearchService] })
export class SearchModule {}

@Module({ controllers: [OpenDataController, ApiKeysController], providers: [ApiKeyGuard] })
export class OpenDataModule {}

@Module({ controllers: [AuthController, MeController, ContactController, MfaController], providers: [AuthService], exports: [AuthService] })
export class AccountsModule {}

@Module({ controllers: [ContributionsController], providers: [ContributionsService], exports: [ContributionsService] })
export class ContributionsModule {}

@Module({
  imports: [ContributionsModule],
  controllers: [AdminAreasController, AdminPlacesController, AdminModerationController, AdminSourcesUsersController, DuplicatesController],
})
export class AdminModule {}

@Module({
  imports: [
    DbModule,
    ThrottlerModule.forRoot([{ name: 'default', ttl: 60_000, limit: Number(process.env.RATE_LIMIT_PER_MIN ?? 240) }]),
    GeoModule, PlacesModule, SearchModule, AccountsModule, ContributionsModule, AdminModule, OpenDataModule,
  ],
  providers: [
    { provide: APP_GUARD, useClass: ThrottlerGuard },
    { provide: APP_GUARD, useClass: AuthGuard },
    { provide: APP_FILTER, useClass: ProblemFilter },
  ],
})
export class AppModule {}
