#ifndef WRAITH_MODULES_H
#define WRAITH_MODULES_H

#include "wraith/engine.h"
#include <string>

namespace wraith::modules {

/**
 * @brief HTTP scraper module — fetches web content.
 */
TaskResult http_scrape(const TaskConfig& config);

/**
 * @brief Data enrichment module — processes and augments data.
 */
TaskResult data_enrich(const TaskConfig& config);

/**
 * @brief Rate limiter module — ensures request spacing.
 */
TaskResult rate_limit_check(const TaskConfig& config);

} // namespace wraith::modules

#endif // WRAITH_MODULES_H