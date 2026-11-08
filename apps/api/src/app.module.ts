import { Module } from '@nestjs/common';
import { DbModule } from './db/db.module';
import { GeoController } from './geo/geo.controller';
import { GeoService } from './geo/geo.service';
import { CategoriesController } from './categories/categories.controller';
import { PlacesController } from './places/places.controller';
import { PlacesService } from './places/places.service';
import { EmergencyController } from './emergency/emergency.controller';
import { SearchController } from './search/search.controller';
import { HealthController } from './health/health.controller';

@Module({
  imports: [DbModule],
  controllers: [GeoController, CategoriesController, PlacesController, EmergencyController, SearchController, HealthController],
  providers: [GeoService, PlacesService],
})
export class AppModule {}
